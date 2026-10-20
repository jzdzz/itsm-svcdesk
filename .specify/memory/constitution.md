<!--
Sync Impact Report:
- Version change: Unversioned template -> 1.0.0
- List of modified principles:
  - [PRINCIPLE_1_NAME] -> I. Specification-First (Strict Order & Pre-Code Receipts)
  - [PRINCIPLE_2_NAME] -> II. Architectural Simplicity & Offline Hermeticity
  - [PRINCIPLE_3_NAME] -> III. Automated Verification & Tier A Compliance
  - [PRINCIPLE_4_NAME] -> IV. Core Domain & Lifecycle Invariants
  - [PRINCIPLE_5_NAME] -> V. AI Transparency & Academic Compliance
- Added sections:
  - Operational & Technical Constraints (replacing [SECTION_2_NAME])
  - Quality Gates & Verification Workflow (replacing [SECTION_3_NAME])
- Removed sections:
  - None
- Follow-up TODOs:
  - None
-->
<!-- ai-generated: 100% - Ratified initial project constitution for svcdesk -->
# svcdesk Constitution

## Core Principles

### I. Specification-First (Strict Order & Pre-Code Receipts)
Specifications MUST precede implementation code under all circumstances. Formal markdown
specifications must be authored in `specs/<feature>/spec.md` with supporting `plan.md` and `tasks.md`.
Per Core spec L1-CORE-5, specifications MUST be committed, pushed, and officially receipted via
`itsmlab.ps1 submit 1 --kind specs` (or `itsmlab.sh`) BEFORE any implementation code is committed
under `src/`. Every commit containing implementation files under `src/` (excluding `src/README.md`)
MUST be an ancestor-verified descendant of the receipted specification commit.
*Rationale*: Prevents premature implementation, enforces contract-driven design, and ensures strict
compliance with course laboratory grading requirements.

### II. Architectural Simplicity & Offline Hermeticity
The `svcdesk` service MUST run as a containerized HTTP service conforming strictly to the course
`docker-compose.yml` contract. All application dependencies MUST be installed during the Docker image
build stage; the runtime environment is sandboxed with egress network access blocked during verification.
Data persistence MUST use named Docker volumes (e.g., `svcdesk-data:/data`), never host-path bind
mounts (which trigger checker failure 1.02). The service MUST support deterministic time manipulation
via the `SVCDESK_TEST_CLOCK: "1"` environment variable and the `X-Test-Clock` HTTP header.
*Rationale*: Guarantees hermetic, reproducible evaluation across local developer environments and
the automated evaluation grader without network or host environment dependencies.

### III. Automated Verification & Tier A Compliance
All functional changes and features MUST be verified locally using the official Tier A verification
suite (`.\itsmlab.ps1 verify 1` or `./itsmlab.sh verify 1`) prior to pushing or opening review. All
Core specifications MUST pass with zero failures (exit code 0). When implementing stretch goal S3,
the dedicated tests service (`docker compose --profile tests run --rm --build tests`) MUST exit 0
and emit `ITSMLAB-TESTS: passed=<n> failed=0` (with n >= 10) as its final stdout line.
*Rationale*: The Tier A verification container represents the ground truth for service correctness
and lab compliance. Running it proactively prevents submission failures.

### IV. Core Domain & Lifecycle Invariants
The architectural decisions formalized in `DECISIONS.md` are non-negotiable system invariants:
- **C1 (SLA Clock Calculation)**: The business-hours clock MUST be uniformly applied for all ticket
  priorities, including P1 incidents. No continuous 24/7 wall-clock exceptions are permitted.
- **C2 (Ticket Immutability)**: Tickets in `closed` status are permanently immutable. Reopening
  closed tickets is forbidden. Recurring or related issues MUST be tracked via a new ticket referencing
  the original ID in `related_to`.
- **C3 (VIP Reporter Elevation)**: Tickets submitted by VIP reporters MUST be elevated to a minimum
  priority of P2 if standard priority matrix calculation yields P3 or P4.
*Rationale*: Ensures architectural consistency, eliminates fragile edge-case scheduling logic, preserves
audit trail integrity, and enforces documented stakeholder business rules.

### V. AI Transparency & Academic Compliance
Every source file (`.py`, `.ts`, `.js`, `.go`, `.java`, etc.) and every markdown document (`.md`)
authored in this repository MUST include an AI-disclosure notice within its first ten lines in the
prescribed format: `ai-generated: <0-100>% - <one line on how>`. Repository hygiene MUST be maintained:
keep the repository public, do not commit personal data or secrets, maintain clean LF line endings
per `.gitattributes`, and keep local virtual environments and `report.json` excluded from git.
*Rationale*: Compliance with course ethics policies and automated checker auditing (`ai-disclosure` check).

## Operational & Technical Constraints

- **Network & Ports**: The service MUST expose its HTTP API on internal port 8080 inside the container.
- **Persistence Store**: Service state MUST be stored in SQLite at `/data/svcdesk.db` residing on the
  named container volume.
- **Deterministic Clocks**: Any date and time logic MUST respect the `X-Test-Clock` header when
  `SVCDESK_TEST_CLOCK` is set to `1`.
- **Language & Runtime**: Python 3.13 (or modern containerized equivalent) with pinned dependencies
  defined in `requirements.txt` and installed at build time in `Dockerfile`.

## Quality Gates & Verification Workflow

1. **Spec Gate**: Complete `specs/<feature>/spec.md` (minimum 500 bytes), `plan.md`, and `tasks.md`
   with proper AI-disclosure headers before touching any source files.
2. **Receipt Gate**: Push specs, obtain receipt via `itsmlab.ps1 submit <lab> --kind specs`, and confirm
   receipt registration before creating or editing files in `src/`.
3. **Implementation Gate**: Develop features in `src/` ensuring all new files have valid AI-disclosure comments.
4. **Local Verification Gate**: Execute `.\itsmlab.ps1 verify <lab>` to confirm all Core checks pass.
5. **CI Gate**: Push to `main` and verify that the GitHub Actions `tier-a` workflow completes green.

## Governance

This Constitution is the foundational operational document for the `svcdesk` service repository.
It supersedes informal agreements and ad-hoc practices. All specifications, architecture decisions,
and pull requests MUST be validated against the principles and quality gates established herein.

Amendments to this Constitution require:
1. Documentation of the business or architectural rationale in the commit message or an accompanying decision record.
2. Verification that proposed changes do not violate course requirements or active `DECISIONS.md` baselines.
3. Version increment adhering to Semantic Versioning:
   - **MAJOR**: Removals, breaking alterations, or structural redefinitions of core principles.
   - **MINOR**: Addition of new principles, quality gates, or materially expanded operational constraints.
   - **PATCH**: Non-semantic clarifications, typographical corrections, or minor wording refinements.

**Version**: 1.0.0 | **Ratified**: 2026-10-19 | **Last Amended**: 2026-10-19
