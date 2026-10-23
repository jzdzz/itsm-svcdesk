# ai-generated: 90% - implementation of DORA metrics matching METRIC-SPEC.md - reviewed by me
from datetime import datetime, timezone
import math
from typing import Any, Dict, List, Optional, Set, Tuple


def parse_rfc3339(dt_str: str) -> datetime:
    """Parses RFC 3339 timestamp into UTC datetime."""
    if not isinstance(dt_str, str):
        raise ValueError("Invalid timestamp")
    if dt_str.endswith("Z"):
        dt_str = dt_str[:-1] + "+00:00"
    dt = datetime.fromisoformat(dt_str)
    return dt.astimezone(timezone.utc)


def round_half_up(val: float, decimals: int = 0) -> float:
    """Rounds half-up as required by R-03."""
    factor = 10**decimals
    return math.floor(val * factor + 0.5) / factor


def compute_median(values: List[int]) -> Optional[int]:
    """Computes median according to R-03 and R-04."""
    if not values:
        return None
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    if n % 2 == 1:
        return sorted_vals[n // 2]
    mid1 = sorted_vals[n // 2 - 1]
    mid2 = sorted_vals[n // 2]
    return int(round_half_up((mid1 + mid2) / 2.0))


def compute_dora_metrics(data: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(data, dict):
        raise ValueError("Request body must be an object")

    # Validate window
    if "window" not in data or not isinstance(data["window"], dict):
        raise ValueError("Missing or invalid window")

    w_from_str = data["window"].get("from")
    w_to_str = data["window"].get("to")
    if not w_from_str or not w_to_str:
        raise ValueError("Window requires 'from' and 'to'")

    w_from = parse_rfc3339(w_from_str)
    w_to = parse_rfc3339(w_to_str)
    if w_to <= w_from:
        raise ValueError("Window 'to' must be strictly after 'from'")

    # Validate events
    if "events" not in data or not isinstance(data["events"], list):
        raise ValueError("Events field must be an array")

    raw_events = data["events"]

    # Deduplicate events by event_id (R-05: first occurrence wins)
    seen_event_ids: Set[str] = set()
    events: List[Dict[str, Any]] = []
    for ev in raw_events:
        if not isinstance(ev, dict) or "event_id" not in ev:
            raise ValueError("Invalid event structure")
        eid = ev["event_id"]
        if eid not in seen_event_ids:
            seen_event_ids.add(eid)
            events.append(ev)

    # Empty log check (L2-CORE-2.07)
    if not events:
        return {
            "spec_version": "1.0.0",
            "window": {"from": w_from_str, "to": w_to_str},
            "deployment_frequency_per_day": 0.0,
            "change_lead_time_seconds_p50": None,
            "failed_deployment_recovery_time_seconds_p50": None,
            "change_fail_rate": None,
            "deployment_rework_rate": None,
            "counts": {
                "deployments": 0,
                "successful_deployments": 0,
                "failed_deployments": 0,
                "recovered_failures": 0,
                "open_failures": 0,
                "rework_deployments": 0,
                "lead_time_pairs": 0,
                "changes": 0,
            },
            "anomalies": {
                "negative_lead_time_pairs": 0,
                "deployments_without_commits": 0,
                "commits_never_on_main": 0,
                "revert_chains_collapsed": 0,
                "overlapping_incident_pairs": 0,
            },
            "ground_truth": {
                "changes_delivered": 0,
                "true_change_lead_time_seconds_p50": None,
            },
        }

    # Group by types and build indices
    commits_by_sha: Dict[str, Dict[str, Any]] = {}
    deployments: List[Dict[str, Any]] = []
    incidents_by_id: Dict[str, Dict[str, Any]] = {}

    for ev in events:
        etype = ev.get("type")
        if etype == "commit":
            sha = ev.get("sha")
            if not sha or sha in commits_by_sha:
                raise ValueError("Duplicate or missing commit SHA")
            commits_by_sha[sha] = ev
        elif etype == "deployment":
            deployments.append(ev)
        elif etype == "incident":
            inc_id = ev.get("incident_id")
            phase = ev.get("phase")
            if not inc_id or phase not in ("opened", "resolved"):
                raise ValueError("Invalid incident")
            if inc_id not in incidents_by_id:
                incidents_by_id[inc_id] = {
                    "incident_id": inc_id,
                    "opened": None,
                    "resolved": None,
                    "deployments": [],
                }
            inc_obj = incidents_by_id[inc_id]
            ev_at = parse_rfc3339(ev["at"])
            if phase == "opened":
                if inc_obj["opened"] is not None:
                    raise ValueError(f"Duplicate opened for {inc_id}")
                inc_obj["opened"] = ev_at
                inc_obj["deployments"] = ev.get("deployments", [])
            elif phase == "resolved":
                if inc_obj["resolved"] is not None:
                    raise ValueError(f"Duplicate resolved for {inc_id}")
                inc_obj["resolved"] = ev_at
        else:
            raise ValueError(f"Unknown event type: {etype}")

    # Validate well-formedness references
    all_dep_ids = {
        d["deployment_id"] for d in deployments if "deployment_id" in d
    }
    for inc_id, inc_obj in incidents_by_id.items():
        if inc_obj["resolved"] is not None and inc_obj["opened"] is None:
            raise ValueError(f"Incident {inc_id} resolved without opened")
        for dep_id in inc_obj["deployments"]:
            if dep_id not in all_dep_ids:
                raise ValueError(f"Incident references unknown deployment {dep_id}")

    revert_chains_collapsed = 0
    for sha, c in commits_by_sha.items():
        reverts = c.get("reverts")
        chg_id = c.get("change_id")
        if reverts is not None:
            revert_chains_collapsed += 1
            if chg_id is not None:
                raise ValueError(
                    f"Commit {sha} has both reverts and change_id"
                )
            if reverts not in commits_by_sha:
                raise ValueError(f"Commit {sha} reverts unknown sha {reverts}")
        else:
            if chg_id is None:
                raise ValueError(
                    f"Commit {sha} missing change_id while reverts is null"
                )

    for d in deployments:
        for csha in d.get("commits", []):
            if csha not in commits_by_sha:
                raise ValueError(f"Deployment references unknown commit {csha}")
        cb = d.get("caused_by")
        if cb is not None and cb not in incidents_by_id:
            raise ValueError(f"Deployment caused_by unknown incident {cb}")

    # Resolve transitive change_id (R-06)
    commit_to_change: Dict[str, str] = {}
    for sha in commits_by_sha:
        curr = sha
        visited = set()
        while commits_by_sha[curr].get("reverts") is not None:
            visited.add(curr)
            curr = commits_by_sha[curr]["reverts"]
            if curr in visited:
                raise ValueError("Cyclic revert detected")
        resolved_change_id = commits_by_sha[curr].get("change_id")
        commit_to_change[sha] = resolved_change_id

    # Earliest commit instant per change (R-07)
    change_first_commit_at: Dict[str, datetime] = {}
    for sha, c in commits_by_sha.items():
        cid = commit_to_change[sha]
        c_at = parse_rfc3339(c["at"])
        if cid not in change_first_commit_at or c_at < change_first_commit_at[cid]:
            change_first_commit_at[cid] = c_at

    # Scope filtering (R-01, R-02): production deployments in window [from, to)
    window_deployments: List[Dict[str, Any]] = []
    for d in deployments:
        if d.get("environment") == "production":
            d_at = parse_rfc3339(d["at"])
            if w_from <= d_at < w_to:
                window_deployments.append({**d, "parsed_at": d_at})

    # Sort window deployments by at ascending
    window_deployments.sort(key=lambda x: x["parsed_at"])

    # Metrics calculation
    num_deployments = len(window_deployments)
    num_successful = sum(
        1 for d in window_deployments if d.get("outcome") == "success"
    )
    num_failed = sum(
        1 for d in window_deployments if d.get("outcome") == "failure"
    )

    # R-11: Deployment Frequency
    window_duration_seconds = (w_to - w_from).total_seconds()
    window_days = window_duration_seconds / 86400.0
    deployment_frequency_per_day = round_half_up(
        num_deployments / window_days, 6
    )

    # R-14: Change Fail Rate
    change_fail_rate = (
        round_half_up(num_failed / num_deployments, 6)
        if num_deployments > 0
        else None
    )

    # R-15: Deployment Rework Rate
    rework_count = sum(
        1
        for d in window_deployments
        if d.get("unplanned") is True and d.get("caused_by") is not None
    )
    deployment_rework_rate = (
        round_half_up(rework_count / num_deployments, 6)
        if num_deployments > 0
        else None
    )

    # R-08, R-09, R-10: Lead Time & Related Anomalies
    lead_time_durations: List[int] = []
    shas_paired: Set[str] = set()
    negative_lead_time_pairs = 0
    deployments_without_commits = 0

    for d in window_deployments:
        d_commits = d.get("commits", [])
        if not d_commits:
            deployments_without_commits += 1

        if d.get("outcome") == "success":
            for sha in d_commits:
                if sha not in shas_paired:
                    shas_paired.add(sha)
                    c_at = parse_rfc3339(commits_by_sha[sha]["at"])
                    diff = int(round((d["parsed_at"] - c_at).total_seconds()))
                    if diff < 0:
                        negative_lead_time_pairs += 1
                        diff = 0
                    lead_time_durations.append(diff)

    change_lead_time_seconds_p50 = compute_median(lead_time_durations)

    # E3: Commits never on main
    prod_window_shas: Set[str] = set()
    for d in window_deployments:
        for sha in d.get("commits", []):
            prod_window_shas.add(sha)

    commits_never_on_main = sum(
        1 for sha in prod_window_shas if commits_by_sha[sha].get("branch") != "main"
    )

    # R-12, R-13: Recovery Time & Open Failures
    recovery_durations: List[int] = []
    open_failures = 0
    recovered_failures = 0

    for d in window_deployments:
        if d.get("outcome") == "failure":
            dep_id = d["deployment_id"]
            covering_candidates = []
            for inc in incidents_by_id.values():
                if dep_id in inc.get("deployments", []):
                    covering_candidates.append(inc)

            if not covering_candidates:
                open_failures += 1
            else:
                # Lowest opened, tie: lowest incident_id
                covering_candidates.sort(
                    key=lambda x: (
                        x["opened"]
                        if x["opened"] is not None
                        else datetime.max.replace(tzinfo=timezone.utc),
                        x["incident_id"],
                    )
                )
                best_inc = covering_candidates[0]
                if best_inc["resolved"] is None:
                    open_failures += 1
                else:
                    recovered_failures += 1
                    rec_diff = int(
                        round(
                            (best_inc["resolved"] - d["parsed_at"]).total_seconds()
                        )
                    )
                    if rec_diff < 0:
                        rec_diff = 0
                    recovery_durations.append(rec_diff)

    failed_deployment_recovery_time_seconds_p50 = compute_median(
        recovery_durations
    )

    # E6: Overlapping incidents
    incidents_list = list(incidents_by_id.values())
    overlapping_incident_pairs = 0
    n_inc = len(incidents_list)
    for i in range(n_inc):
        for j in range(i + 1, n_inc):
            inc_a = incidents_list[i]
            inc_b = incidents_list[j]
            if inc_a["opened"] is None or inc_b["opened"] is None:
                continue
            end_a = inc_a["resolved"] if inc_a["resolved"] is not None else w_to
            end_b = inc_b["resolved"] if inc_b["resolved"] is not None else w_to
            # Check intersection [opened, end)
            if inc_a["opened"] < end_b and inc_b["opened"] < end_a:
                overlapping_incident_pairs += 1

    # R-16, R-17: Ground Truth
    change_first_succ_deployment: Dict[str, datetime] = {}
    for d in window_deployments:
        if d.get("outcome") == "success":
            for sha in d.get("commits", []):
                cid = commit_to_change[sha]
                if cid not in change_first_succ_deployment:
                    change_first_succ_deployment[cid] = d["parsed_at"]

    changes_delivered = len(change_first_succ_deployment)
    true_lead_times: List[int] = []
    for cid, first_dep_at in change_first_succ_deployment.items():
        first_c_at = change_first_commit_at[cid]
        diff = int(round((first_dep_at - first_c_at).total_seconds()))
        if diff < 0:
            diff = 0
        true_lead_times.append(diff)

    true_change_lead_time_seconds_p50 = compute_median(true_lead_times)

    return {
        "spec_version": "1.0.0",
        "window": {"from": w_from_str, "to": w_to_str},
        "deployment_frequency_per_day": deployment_frequency_per_day,
        "change_lead_time_seconds_p50": change_lead_time_seconds_p50,
        "failed_deployment_recovery_time_seconds_p50": failed_deployment_recovery_time_seconds_p50,
        "change_fail_rate": change_fail_rate,
        "deployment_rework_rate": deployment_rework_rate,
        "counts": {
            "deployments": num_deployments,
            "successful_deployments": num_successful,
            "failed_deployments": num_failed,
            "recovered_failures": recovered_failures,
            "open_failures": open_failures,
            "rework_deployments": rework_count,
            "lead_time_pairs": len(lead_time_durations),
            "changes": len(change_first_commit_at),
        },
        "anomalies": {
            "negative_lead_time_pairs": negative_lead_time_pairs,
            "deployments_without_commits": deployments_without_commits,
            "commits_never_on_main": commits_never_on_main,
            "revert_chains_collapsed": revert_chains_collapsed,
            "overlapping_incident_pairs": overlapping_incident_pairs,
        },
        "ground_truth": {
            "changes_delivered": changes_delivered,
            "true_change_lead_time_seconds_p50": true_change_lead_time_seconds_p50,
        },
    }