# ai-generated: 100% - Gemini
from datetime import datetime, timedelta
from typing import List, Optional, Literal
import uuid
from fastapi import FastAPI, Header, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
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

def parse_test_clock(x_test_clock: Optional[str]) -> datetime:
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
        elif t.state == "closed" and t.closed_at and (now - t.closed_at) <= window_limit:
            valid = True
            t.state = "in_progress"
            t.closed_at = None
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