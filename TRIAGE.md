---
lab5_triage:
  image: ghcr.io/jzdzz/itsm-svcdesk@sha256:25080c8b908dd0eb0d3e4b1b8be853bb239c4f4f9f4fcee6447634b947438996
  sarif_receipt: 441
---
<!-- ai-generated: 100% - Gemini drafted the triage table and bake-off analysis from the SARIF and labels data -->
# Triage

What the gates and the reporting scanners found on my service, and what I did about each (CI-SPEC.md P-11, P-12).
One row per rule of one tool; a row may cover several locations, and the Reason says which. Tool is the tool id of
P-15 (`trivy`, `grype`, `osv-scanner`, `gitleaks`, `semgrep`). Decision is one of `fix`, `ignore`,
`false-positive`, `accept`.

| Tool | Rule | Decision | Reason |
|---|---|---|---|
| trivy | CVE-2024-24762 | fix | Removed unused `python-multipart==0.0.6` from `requirements.txt` and pinned `fastapi==0.141.1`, `uvicorn==0.52.4`, `pydantic==2.12.2`, and `httpx==0.28.1` to eliminate HIGH/CRITICAL CVEs on `requirements.txt`. |
| trivy | CVE-2023-45853 | fix | Pinned `FROM python:3.13-slim@sha256:e48f59cdba69a3cbd9ed2cf0f348d90d45a8d350d98134cf1070bc106ee9ed90`, ran `apt-get update && apt-get upgrade -y` (upgrading `zlib1g` to `1:1.3.dfsg+really1.3.1-1+deb13u1`), and uninstalled `pip` and `setuptools` in `Dockerfile`. |
| semgrep | dockerfile.security.missing-user.missing-user | accept | Reported at `Dockerfile:17`; the container runs an isolated stateless student microservice in a local Docker Compose test network without host volume mounts or privileged capabilities. |
| semgrep | python.lang.security.audit.insecure-transport.urllib.insecure-urlopen.insecure-urlopen | false-positive | Reported at `src/tests.py:23`, `src/tests.py:32`, and `src/tests.py:78`; these calls are internal smoke tests connecting to the local `svcdesk` container over the internal Docker Compose bridge network (`http://svcdesk:8000`). |
| semgrep | python.lang.security.audit.insecure-transport.urllib.insecure-request-object.insecure-request-object | false-positive | Reported at `src/tests.py:42` and `src/tests.py:54`; `urllib.request.Request` targets only the fixed internal test URL `http://svcdesk:8000` during automated CI smoke testing. |
| semgrep | python.lang.security.audit.dynamic-urllib-use-detected.dynamic-urllib-use-detected | false-positive | Reported at `src/tests.py:43`, `src/tests.py:55`, `src/tests.py:67`, `src/tests.py:88`, and `generate_stretch.py:19`; the URLs are constructed exclusively from hardcoded local test base URLs and controlled test paths, never from untrusted user input. |

## Bake-off

Across the 9 seeded defects in `lab5-canary`, each tool achieved the following confusion matrix metrics:
- **gitleaks**: `tp=3, fp=0, fn=6, precision=1.0, recall=0.3333, f1=0.5` — caught all three hardcoded secrets (`C01` in `lab5-canary/config/backup.sh`, `C03` in `lab5-canary/config/github.py`, and `C06` in `lab5-canary/config/search.py`) with zero false positives.
- **trivy**: `tp=3, fp=0, fn=6, precision=1.0, recall=0.3333, f1=0.5` — detected both vulnerable dependencies (`D03` `Jinja2` and `D04` `python-multipart` in `lab5-canary/requirements.txt`) plus one secret (`C03` GitHub PAT in `lab5-canary/config/github.py`) with zero false positives.
- **grype**: `tp=2, fp=0, fn=7, precision=1.0, recall=0.2222, f1=0.3636` — found both vulnerable dependencies (`D03` and `D04`) with perfect precision, while leaving code and secret defects out of scope.
- **osv-scanner**: `tp=2, fp=0, fn=7, precision=1.0, recall=0.2222, f1=0.3636` — identically matched the two vulnerable dependencies (`D03` and `D04`) with zero false positives.
- **semgrep**: `tp=3, fp=3, fn=6, precision=0.5, recall=0.3333, f1=0.4` — identified `A04` (`insecure-transport` disabled cert validation in `avatar_fetch.py:7`), `A11` (`injection` via `eval()` in `sla_formula.py:6`), and `C06` (`secret` generic API key in `search.py:3`), but generated 3 false positives (`direct-use-of-jinja2` in `email_render.py:4` and two SQL injection rules on parameterized/safe count queries in `ticket_counts.py:8`).

**Which detector to put in a gate and why:** I would place **Trivy** (`precision=1.0, fp=0, tp=3, f1=0.5`) and **Gitleaks** (`precision=1.0, fp=0, tp=3, f1=0.5`) in blocking CI gates, while keeping **Semgrep** (`precision=0.5, fp=3, f1=0.4`) in report-only mode. A blocking gate requires near-1.0 precision so developers are not trained to bypass broken builds caused by false alarms; combining Gitleaks and Trivy covers 5 of the 9 seeded defects (all 3 secrets and both vulnerable dependencies) with 0 false positives, whereas gating on Semgrep would block the pipeline on 3 false positives in `lab5-canary` alone (plus 9 benign findings in `src/tests.py` and `Dockerfile`).

**Surprising cells:** Two cells stood out: first, **Trivy** achieved `tp=3` rather than `2` because its filesystem scan includes built-in secret detection that caught the GitHub PAT (`C03`), tying Gitleaks and Semgrep for the highest recall (`0.3333`) and tying Gitleaks for the top F1 score (`0.5`). Second, **Semgrep** had `fp=3` (`precision=0.5`) because its syntactic heuristics flagged safe template rendering (`email_render.py`) and integer-typed/allowlisted SQL queries (`ticket_counts.py`), while missing `A03` (`path-traversal` in `attachment_read.py`).

**What the defects none of the five found have in common:** None of the five scanners detected `A03` (`path-traversal`, `CWE-22` in `lab5-canary/app/attachment_read.py:9-10`) or `A12` (`access-control` / IDOR, `CWE-639` in `lab5-canary/app/ticket_access.py:12-17`). Both defects depend on semantic application context and business logic rather than an obvious dangerous sink or signature: `A03` uses `os.path.join(ATTACH_ROOT, name)` followed by `.open()` without verifying that the resolved path stays inside `ATTACH_ROOT`, and `A12` fetches a ticket by ID without checking whether `requester_id` owns that ticket. Static pattern matchers and dependency/secret scanners cannot infer missing authorization checks or path canonicalization invariants without deeper dataflow or architectural understanding.

**Why every recall here is an upper bound:** Every recall figure in this table (`0.2222` to `0.3333`) is an optimistic upper bound because the 9 defects in `lab5-canary` are textbook, self-contained, single-file seeded vulnerabilities designed specifically to match known CWE archetypes, standard token prefixes (`ghp_`), and well-known historical CVEs (`Jinja2==2.10`, `python-multipart==0.0.5`). In production systems, vulnerabilities span multiple modules, custom wrappers, indirect configuration layers, and novel business logic flaws that flatter no static rule set, meaning real-world recall is strictly lower than on a curated benchmark.