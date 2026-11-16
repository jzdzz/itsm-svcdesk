# ai-generated: 100% - Gemini implemented SARIF confusion matrix rules P-14..P-23 from CI-SPEC.md
"""bakeoff.py - scanner SARIF + a labels file -> a per-tool confusion matrix (CI-SPEC.md P-23)."""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.parse

CLASS_CWES: dict[str, set[int]] = {
    "secret": {259, 260, 321, 798},
    "injection": {74, 77, 78, 79, 80, 88, 89, 90, 91, 94, 95, 96, 611, 776, 917, 943, 1336},
    "deserialization": {502},
    "weak-crypto": {261, 326, 327, 328, 330, 331, 338, 759, 760, 916},
    "insecure-transport": {295, 297, 319, 322, 757},
    "path-traversal": {22, 23, 35, 36, 73},
    "ssrf": {918},
    "vulnerable-dependency": {937, 1035, 1104, 1395},
    "misconfiguration": {16, 215, 250, 489, 668, 732, 1188},
    "access-control": {284, 285, 639, 862, 863},
}

VALID_CLASSES = set(CLASS_CWES.keys())
CWE_PATTERN = re.compile(r"(?<![A-Za-z0-9])[Cc][Ww][Ee]-([0-9]+)")
TOKEN_PATTERN = re.compile(r"[A-Za-z0-9._-]+")
PEP503_PATTERN = re.compile(r"[-_.]+")


def normalize_pkg(name: str) -> str:
    return PEP503_PATTERN.sub("-", name.lower())


def extract_tokens(text: str) -> set[str]:
    tokens: set[str] = set()
    for match in TOKEN_PATTERN.findall(text):
        trimmed = match.strip("._-")
        if trimmed:
            tokens.add(normalize_pkg(trimmed))
    return tokens


def is_strict_int(val: object) -> bool:
    return isinstance(val, int) and not isinstance(val, bool)


def normalize_tool_id(run: dict) -> str:
    tool = run.get("tool")
    if not isinstance(tool, dict):
        return "unknown"
    driver = tool.get("driver")
    if not isinstance(driver, dict):
        return "unknown"
    name = driver.get("name")
    if not isinstance(name, str):
        return "unknown"
    cleaned = name.strip().lower()
    if not cleaned:
        return "unknown"
    if cleaned in {"trivy", "grype", "osv-scanner", "gitleaks"}:
        return cleaned
    if cleaned in {"semgrep", "semgrep oss", "semgrep ce", "semgrep community edition", "semgrep pro"}:
        return "semgrep"
    slug = re.sub(r"[^a-z0-9]+", "-", cleaned).strip("-")
    return slug if slug else "unknown"


def resolve_in_set_path(uri: str, set_root: str) -> str | None:
    decoded = urllib.parse.unquote(uri)
    if decoded.lower().startswith("file://"):
        decoded = decoded[7:]
    if decoded.startswith("./"):
        decoded = decoded[2:]
    parts = decoded.split("/")
    last_idx = -1
    for idx, comp in enumerate(parts):
        if comp == set_root:
            last_idx = idx
    if last_idx == -1:
        return None
    return "/".join(parts[last_idx:])


def get_rule_tags(run: dict, rule_id: object) -> list[str]:
    if not isinstance(rule_id, str):
        return []
    tool = run.get("tool")
    if not isinstance(tool, dict):
        return []
    driver = tool.get("driver")
    if not isinstance(driver, dict):
        return []
    rules = driver.get("rules")
    if not isinstance(rules, list):
        return []
    for r in rules:
        if isinstance(r, dict) and r.get("id") == rule_id:
            props = r.get("properties")
            if isinstance(props, dict) and isinstance(props.get("tags"), list):
                return [t for t in props["tags"] if isinstance(t, str)]
            return []
    return []


def classify_result(tool_id: str, result: dict, rule_tags: list[str]) -> set[str]:
    props = result.get("properties")
    if isinstance(props, dict):
        prop_class = props.get("class")
        if isinstance(prop_class, str) and prop_class in VALID_CLASSES:
            return {prop_class}

    if tool_id == "gitleaks":
        return {"secret"}
    if tool_id in {"grype", "osv-scanner"}:
        return {"vulnerable-dependency"}
    if tool_id == "trivy":
        trivy_classes: set[str] = set()
        for t in rule_tags:
            tl = t.lower()
            if tl == "vulnerability":
                trivy_classes.add("vulnerable-dependency")
            elif tl == "secret":
                trivy_classes.add("secret")
            elif tl == "misconfiguration":
                trivy_classes.add("misconfiguration")
        if trivy_classes:
            return trivy_classes

    all_tags: list[str] = []
    if isinstance(props, dict) and isinstance(props.get("tags"), list):
        all_tags.extend([t for t in props["tags"] if isinstance(t, str)])
    all_tags.extend(rule_tags)

    cwe_nums: set[int] = set()
    for tag in all_tags:
        for m in CWE_PATTERN.finditer(tag):
            cwe_nums.add(int(m.group(1)))

    matched_classes: set[str] = set()
    for cls, cwes in CLASS_CWES.items():
        if cwe_nums & cwes:
            matched_classes.add(cls)

    return matched_classes if matched_classes else {"other"}


def is_empty_suppressions(sup: object) -> bool:
    if sup is None or sup is False or sup == 0 or sup == "":
        return True
    if isinstance(sup, (list, dict)) and len(sup) == 0:
        return True
    return False


def confusion_matrix(labels: dict, sarif_documents: list[dict]) -> dict:
    set_root = labels["set"]
    defects = labels["defects"]

    tool_findings: dict[str, list[dict]] = {}

    for doc in sarif_documents:
        if not isinstance(doc, dict):
            continue
        runs = doc.get("runs")
        if not isinstance(runs, list):
            continue
        for run in runs:
            if not isinstance(run, dict):
                continue
            tool_id = normalize_tool_id(run)
            if tool_id not in tool_findings:
                tool_findings[tool_id] = []

            results = run.get("results")
            if not isinstance(results, list):
                continue

            for res in results:
                if not isinstance(res, dict):
                    continue
                kind = res.get("kind")
                if kind is not None and kind != "fail":
                    continue
                if not is_empty_suppressions(res.get("suppressions")):
                    continue

                locations = res.get("locations")
                if not isinstance(locations, list) or len(locations) == 0:
                    continue
                first_loc = locations[0]
                if not isinstance(first_loc, dict):
                    continue
                phys = first_loc.get("physicalLocation")
                if not isinstance(phys, dict):
                    continue
                art = phys.get("artifactLocation")
                if not isinstance(art, dict):
                    continue
                uri = art.get("uri")
                if not isinstance(uri, str) or not uri:
                    continue

                in_set_file = resolve_in_set_path(uri, set_root)
                if in_set_file is None:
                    continue

                start_line: int | None = None
                end_line: int | None = None
                region = phys.get("region")
                if isinstance(region, dict):
                    sl = region.get("startLine")
                    if is_strict_int(sl) and sl >= 1:
                        start_line = sl
                        el = region.get("endLine")
                        if is_strict_int(el) and el >= start_line:
                            end_line = el
                        else:
                            end_line = start_line

                raw_rule_id = res.get("ruleId")
                rule_id = raw_rule_id if isinstance(raw_rule_id, str) else None
                rule_tags = get_rule_tags(run, rule_id)
                classes = classify_result(tool_id, res, rule_tags)

                msg_tokens: set[str] = set()
                msg = res.get("message")
                if isinstance(msg, dict) and isinstance(msg.get("text"), str):
                    msg_tokens = extract_tokens(msg["text"])

                tool_findings[tool_id].append({
                    "rule_id": rule_id,
                    "file": in_set_file,
                    "start_line": start_line,
                    "end_line": end_line,
                    "classes": classes,
                    "msg_tokens": msg_tokens,
                })

    tools_out: dict[str, dict] = {}
    for tool_id, findings in tool_findings.items():
        matched_defect_indices: set[int] = set()
        fp_keys: set[tuple[str | None, str, int | None, int | None]] = set()

        for f in findings:
            matched_any = False
            for idx, d in enumerate(defects):
                if f["file"] != d["file"]:
                    continue
                d_class = d["class"]
                if d_class not in f["classes"]:
                    continue
                if d_class == "vulnerable-dependency":
                    pkg = normalize_pkg(d["package"])
                    if pkg in f["msg_tokens"]:
                        matched_any = True
                        matched_defect_indices.add(idx)
                else:
                    if f["start_line"] is not None and f["end_line"] is not None:
                        if f["start_line"] <= d["end_line"] and d["start_line"] <= f["end_line"]:
                            matched_any = True
                            matched_defect_indices.add(idx)

            if not matched_any:
                fp_keys.add((f["rule_id"], f["file"], f["start_line"], f["end_line"]))

        tp = len(matched_defect_indices)
        fn = len(defects) - tp
        fp = len(fp_keys)

        precision = round(tp / (tp + fp), 4) if (tp + fp) > 0 else None
        recall = round(tp / (tp + fn), 4) if (tp + fn) > 0 else None
        f1 = round((2 * tp) / (2 * tp + fp + fn), 4) if (2 * tp + fp + fn) > 0 else None

        tools_out[tool_id] = {
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "precision": precision,
            "recall": recall,
            "f1": f1,
        }

    return {"set": set_root, "defects": len(defects), "tools": tools_out}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="per-tool confusion matrix of SARIF against labels (CI-SPEC.md P-23)")
    parser.add_argument("--labels", required=True, help="the labels file (P-14)")
    parser.add_argument("sarif", nargs="+", help="SARIF 2.1.0 files")
    args = parser.parse_args(argv)
    with open(args.labels, encoding="utf-8") as fh:
        labels = json.load(fh)
    documents = []
    for path in args.sarif:
        with open(path, encoding="utf-8") as fh:
            documents.append(json.load(fh))
    json.dump(confusion_matrix(labels, documents), sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())