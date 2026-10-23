# ai-generated: 90% - FastAPI svcdesk extended with DORA metrics and lifecycle stream
from datetime import datetime, timedelta, timezone
import math
from typing import Any, Dict, List, Literal, Optional, Set
import uuid
from fastapi import FastAPI, Header, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import pytz

app = FastAPI(title="svcdesk", version="1.0.0")

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    err_msg = "Validation error"
    if exc.errors():
        first_err = exc.errors()[0]
        loc = " -> ".join(str(l) for l in first_err.get("loc", []))
        msg = first_err.get("msg", "invalid field")
        err_msg = f"{loc}: {msg}" if loc else msg
    return JSONResponse(
        status_code=422,
        content={"error": {"code": "validation", "message": err_msg}}
    )

tickets_db = {}
WARSAW_TZ = pytz.timezone("Europe/Warsaw")

class Reporter(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: Optional[str] = None
    vip: Optional[bool] = False

class TicketCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field("", max_length=4000)
    reporter: Reporter
    impact: Literal[1, 2, 3]
    urgency: Literal[1, 2, 3]
    related_to: Optional[str] = None

class SLAModel(BaseModel):
    ack_due_at: datetime
    resolve_due_at: datetime

class Ticket(BaseModel):
    id: str
    title: str
    description: str
    reporter: Reporter
    impact: int
    urgency: int
    priority: Literal["P1", "P2", "P3", "P4"]
    state: Literal["new", "acknowledged", "in_progress", "resolved", "closed"]
    created_at: datetime
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    related_to: Optional[str] = None
    sla: SLAModel

class SLAResponse(BaseModel):
    priority: str
    ack_due_at: datetime
    resolve_due_at: datetime
    ack_breached: bool
    resolve_breached: bool
    paused: bool

def parse_test_clock(x_test_clock: Optional[str]):
    if not x_test_clock:
        return datetime.now(pytz.UTC)
    try:
        dt = datetime.fromisoformat(x_test_clock.replace("Z", "+00:00"))
        return dt.astimezone(pytz.UTC)
    except Exception:
        return JSONResponse(
            status_code=400,
            content={"error": {"code": "validation", "message": "Invalid X-Test-Clock format"}}
        )

def compute_priority(impact: int, urgency: int, is_vip: bool) -> str:
    matrix = {
        (1, 1): "P1", (1, 2): "P2", (1, 3): "P3",
        (2, 1): "P2", (2, 2): "P3", (2, 3): "P4",
        (3, 1): "P3", (3, 2): "P4", (3, 3): "P4",
    }
    base_priority = matrix.get((impact, urgency), "P4")
    if is_vip and base_priority in ["P3", "P4"]:
        return "P2"
    return base_priority

def add_business_hours(start_dt: datetime, hours: float) -> datetime:
    current = start_dt.astimezone(WARSAW_TZ)
    remaining_minutes = int(hours * 60)
    
    while remaining_minutes > 0:
        if current.weekday() >= 5:
            days_to_add = 7 - current.weekday()
            current = (current + timedelta(days=days_to_add)).replace(hour=8, minute=0, second=0, microsecond=0)
            continue
            
        if current.hour < 8:
            current = current.replace(hour=8, minute=0, second=0, microsecond=0)
            continue
        elif current.hour >= 16:
            current = (current + timedelta(days=1)).replace(hour=8, minute=0, second=0, microsecond=0)
            continue
            
        closing_time = current.replace(hour=16, minute=0, second=0, microsecond=0)
        available_minutes = int((closing_time - current).total_seconds() / 60)
        
        if remaining_minutes <= available_minutes:
            current += timedelta(minutes=remaining_minutes)
            remaining_minutes = 0
        else:
            remaining_minutes -= available_minutes
            current = (current + timedelta(days=1)).replace(hour=8, minute=0, second=0, microsecond=0)
            
    return current.astimezone(pytz.UTC)

def calculate_sla(priority: str, created_at: datetime) -> SLAModel:
    targets = {
        "P1": (0.25, 4),
        "P2": (1, 8),
        "P3": (4, 24),
        "P4": (8, 72)
    }
    ack_h, res_h = targets[priority]
    ack_due = add_business_hours(created_at, ack_h)
    res_due = add_business_hours(created_at, res_h)
    return SLAModel(ack_due_at=ack_due, resolve_due_at=res_due)

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "svcdesk"}

@app.post("/tickets", status_code=status.HTTP_201_CREATED, response_model=Ticket)
def create_ticket(payload: TicketCreate, x_test_clock: Optional[str] = Header(None)):
    now = parse_test_clock(x_test_clock)
    if isinstance(now, JSONResponse):
        return now
    ticket_id = str(uuid.uuid4())
    is_vip = payload.reporter.vip if payload.reporter.vip is not None else False
    priority = compute_priority(payload.impact, payload.urgency, is_vip)
    sla = calculate_sla(priority, now)
    
    ticket = Ticket(
        id=ticket_id,
        title=payload.title,
        description=payload.description or "",
        reporter=payload.reporter,
        impact=payload.impact,
        urgency=payload.urgency,
        priority=priority,
        state="new",
        created_at=now,
        related_to=payload.related_to,
        sla=sla
    )
    tickets_db[ticket_id] = ticket
    return ticket

@app.get("/tickets", response_model=List[Ticket])
def list_tickets(state: Optional[str] = None, priority: Optional[str] = None):
    result = list(tickets_db.values())
    if state:
        result = [t for t in result if t.state == state]
    if priority:
        result = [t for t in result if t.priority == priority]
    return result

@app.get("/tickets/{ticket_id}", response_model=Ticket)
def get_ticket(ticket_id: str):
    if ticket_id not in tickets_db:
        return JSONResponse(
            status_code=404,
            content={"error": {"code": "not_found", "message": "Ticket not found"}}
        )
    return tickets_db[ticket_id]

@app.get("/tickets/{ticket_id}/sla", response_model=SLAResponse)
def get_ticket_sla(ticket_id: str, x_test_clock: Optional[str] = Header(None)):
    if ticket_id not in tickets_db:
        return JSONResponse(
            status_code=404,
            content={"error": {"code": "not_found", "message": "Ticket not found"}}
        )
    t = tickets_db[ticket_id]
    now = parse_test_clock(x_test_clock)
    if isinstance(now, JSONResponse):
        return now
    
    ack_breached = (now > t.sla.ack_due_at) if t.acknowledged_at is None else (t.acknowledged_at > t.sla.ack_due_at)
    resolve_breached = (now > t.sla.resolve_due_at) if t.state not in ["resolved", "closed"] else ((t.resolved_at and t.resolved_at > t.sla.resolve_due_at) or False)
        
    local_now = now.astimezone(WARSAW_TZ)
    is_weekend = local_now.weekday() >= 5
    is_out_of_hours = local_now.hour < 8 or local_now.hour >= 16
    paused = t.state not in ["resolved", "closed"] and (is_weekend or is_out_of_hours)
    
    return SLAResponse(
        priority=t.priority,
        ack_due_at=t.sla.ack_due_at,
        resolve_due_at=t.sla.resolve_due_at,
        ack_breached=ack_breached,
        resolve_breached=resolve_breached,
        paused=paused
    )

def transition_ticket(ticket_id: str, action: str, x_test_clock: Optional[str]):
    now = parse_test_clock(x_test_clock)
    if isinstance(now, JSONResponse):
        return now
        
    if ticket_id not in tickets_db:
        return JSONResponse(
            status_code=404,
            content={"error": {"code": "not_found", "message": "Ticket not found"}}
        )
    t = tickets_db[ticket_id]
    
    if t.state == "closed":
        return JSONResponse(
            status_code=409,
            content={"error": {"code": "ticket_closed", "message": "Ticket is closed"}}
        )
        
    valid = False
    if action == "ack" and t.state == "new":
        valid = True
        t.state = "acknowledged"
        t.acknowledged_at = now
    elif action == "start" and t.state == "acknowledged":
        valid = True
        t.state = "in_progress"
    elif action == "resolve" and t.state == "in_progress":
        valid = True
        t.state = "resolved"
        t.resolved_at = now
    elif action == "close" and t.state == "resolved":
        valid = True
        t.state = "closed"
        t.closed_at = now
    elif action == "reopen":
        window_limit = timedelta(days=7)
        if t.state == "resolved" and t.resolved_at and (now - t.resolved_at) <= window_limit:
            valid = True
            t.state = "in_progress"
            t.resolved_at = None
        else:
            return JSONResponse(
                status_code=409,
                content={"error": {"code": "reopen_window_expired", "message": "Reopen window expired"}}
            )
            
    if not valid:
        return JSONResponse(
            status_code=409,
            content={"error": {"code": "invalid_transition", "message": "Invalid transition"}}
        )
    return t

@app.post("/tickets/{ticket_id}/ack", response_model=Ticket)
def ack_ticket(ticket_id: str, x_test_clock: Optional[str] = Header(None)):
    return transition_ticket(ticket_id, "ack", x_test_clock)

@app.post("/tickets/{ticket_id}/start", response_model=Ticket)
def start_ticket(ticket_id: str, x_test_clock: Optional[str] = Header(None)):
    return transition_ticket(ticket_id, "start", x_test_clock)

@app.post("/tickets/{ticket_id}/resolve", response_model=Ticket)
def resolve_ticket(ticket_id: str, x_test_clock: Optional[str] = Header(None)):
    return transition_ticket(ticket_id, "resolve", x_test_clock)

@app.post("/tickets/{ticket_id}/close", response_model=Ticket)
def close_ticket(ticket_id: str, x_test_clock: Optional[str] = Header(None)):
    return transition_ticket(ticket_id, "close", x_test_clock)

@app.post("/tickets/{ticket_id}/reopen", response_model=Ticket)
def reopen_ticket(ticket_id: str, x_test_clock: Optional[str] = Header(None)):
    return transition_ticket(ticket_id, "reopen", x_test_clock)

# ==============================================================================
# LABORATORY 2: DORA METRICS & TICKET EVENTS
# ==============================================================================

def parse_rfc3339(dt_str: str) -> datetime:
    if not isinstance(dt_str, str):
        raise ValueError("Invalid timestamp")
    if dt_str.endswith("Z"):
        dt_str = dt_str[:-1] + "+00:00"
    dt = datetime.fromisoformat(dt_str)
    return dt.astimezone(timezone.utc)

def round_half_up(val: float, decimals: int = 0) -> float:
    factor = 10**decimals
    return math.floor(val * factor + 0.5) / factor

def compute_median(values: List[int]) -> Optional[int]:
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

    if "events" not in data or not isinstance(data["events"], list):
        raise ValueError("Events field must be an array")

    seen_event_ids: Set[str] = set()
    events: List[Dict[str, Any]] = []
    for ev in data["events"]:
        if not isinstance(ev, dict) or "event_id" not in ev:
            raise ValueError("Invalid event structure")
        eid = ev["event_id"]
        if eid not in seen_event_ids:
            seen_event_ids.add(eid)
            events.append(ev)

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

    all_dep_ids = {d["deployment_id"] for d in deployments if "deployment_id" in d}
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
                raise ValueError(f"Commit {sha} has both reverts and change_id")
            if reverts not in commits_by_sha:
                raise ValueError(f"Commit {sha} reverts unknown sha {reverts}")
        else:
            if chg_id is None:
                raise ValueError(f"Commit {sha} missing change_id while reverts is null")

    for d in deployments:
        for csha in d.get("commits", []):
            if csha not in commits_by_sha:
                raise ValueError(f"Deployment references unknown commit {csha}")
        cb = d.get("caused_by")
        if cb is not None and cb not in incidents_by_id:
            raise ValueError(f"Deployment caused_by unknown incident {cb}")

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

    change_first_commit_at: Dict[str, datetime] = {}
    for sha, c in commits_by_sha.items():
        cid = commit_to_change[sha]
        c_at = parse_rfc3339(c["at"])
        if cid not in change_first_commit_at or c_at < change_first_commit_at[cid]:
            change_first_commit_at[cid] = c_at

    window_deployments: List[Dict[str, Any]] = []
    for d in deployments:
        if d.get("environment") == "production":
            d_at = parse_rfc3339(d["at"])
            if w_from <= d_at < w_to:
                window_deployments.append({**d, "parsed_at": d_at})

    window_deployments.sort(key=lambda x: x["parsed_at"])

    num_deployments = len(window_deployments)
    num_successful = sum(1 for d in window_deployments if d.get("outcome") == "success")
    num_failed = sum(1 for d in window_deployments if d.get("outcome") == "failure")

    window_duration_seconds = (w_to - w_from).total_seconds()
    window_days = window_duration_seconds / 86400.0
    deployment_frequency_per_day = round_half_up(num_deployments / window_days, 6)

    change_fail_rate = (
        round_half_up(num_failed / num_deployments, 6) if num_deployments > 0 else None
    )

    rework_count = sum(
        1
        for d in window_deployments
        if d.get("unplanned") is True and d.get("caused_by") is not None
    )
    deployment_rework_rate = (
        round_half_up(rework_count / num_deployments, 6) if num_deployments > 0 else None
    )

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

    prod_window_shas: Set[str] = set()
    for d in window_deployments:
        for sha in d.get("commits", []):
            prod_window_shas.add(sha)

    commits_never_on_main = sum(
        1 for sha in prod_window_shas if commits_by_sha[sha].get("branch") != "main"
    )

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
                covering_candidates.sort(
                    key=lambda x: (
                        x["opened"] if x["opened"] is not None else datetime.max.replace(tzinfo=timezone.utc),
                        x["incident_id"],
                    )
                )
                best_inc = covering_candidates[0]
                if best_inc["resolved"] is None:
                    open_failures += 1
                else:
                    recovered_failures += 1
                    rec_diff = int(round((best_inc["resolved"] - d["parsed_at"]).total_seconds()))
                    if rec_diff < 0:
                        rec_diff = 0
                    recovery_durations.append(rec_diff)

    failed_deployment_recovery_time_seconds_p50 = compute_median(recovery_durations)

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
            if inc_a["opened"] < end_b and inc_b["opened"] < end_a:
                overlapping_incident_pairs += 1

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

@app.post("/dora/metrics")
async def post_dora_metrics(request: Request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            status_code=422,
            content={"error": {"code": "validation", "message": "Invalid JSON"}}
        )

    try:
        metrics = compute_dora_metrics(body)
        return metrics
    except ValueError as e:
        return JSONResponse(
            status_code=422,
            content={"error": {"code": "validation", "message": str(e)}}
        )

def format_instant(dt: Optional[datetime]) -> Optional[str]:
    if not dt:
        return None
    utc_dt = dt.astimezone(timezone.utc)
    return utc_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

@app.get("/dora/ticket-events")
def get_ticket_events():
    events = []
    for t in tickets_db.values():
        tid = t.id
        prio = t.priority
        if t.created_at:
            events.append({
                "ticket_id": tid,
                "at": format_instant(t.created_at),
                "phase": "created",
                "priority": prio,
                "state": "new"
            })
        if t.acknowledged_at:
            events.append({
                "ticket_id": tid,
                "at": format_instant(t.acknowledged_at),
                "phase": "acknowledged",
                "priority": prio,
                "state": "acknowledged"
            })
        if t.resolved_at:
            events.append({
                "ticket_id": tid,
                "at": format_instant(t.resolved_at),
                "phase": "resolved",
                "priority": prio,
                "state": "resolved"
            })
        if t.closed_at:
            events.append({
                "ticket_id": tid,
                "at": format_instant(t.closed_at),
                "phase": "closed",
                "priority": prio,
                "state": "closed"
            })
    events.sort(key=lambda x: (x["at"], x["ticket_id"]))
    return events