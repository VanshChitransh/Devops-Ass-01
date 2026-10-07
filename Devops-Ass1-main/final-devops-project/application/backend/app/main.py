"""TicketHub API: a small helpdesk ticketing backend built by Vansh for the DevOps capstone."""
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app import models, schemas
from app.config import settings
from app.db import get_db

app = FastAPI(
    title="TicketHub API",
    version="1.0.0",
    description="Helpdesk tickets: create, list, update, resolve. Built by Vansh.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_methods=["*"],
    allow_headers=["*"],
)
Instrumentator(excluded_handlers=["/metrics", "/health", "/ready"]).instrument(app).expose(app, include_in_schema=False)


@app.get("/", tags=["meta"])
def root():
    return {"app": settings.app_name, "env": settings.app_env, "owner": "Vansh", "docs": "/docs"}


@app.get("/health", tags=["meta"])
def health():
    """Liveness: the process is up and can answer HTTP."""
    return {"status": "healthy"}


@app.get("/ready", tags=["meta"])
def ready(response: Response, db: Session = Depends(get_db)):
    """Readiness: the process can also reach its database."""
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001 - any DB failure means not ready
        response.status_code = 503
        return {"status": "not ready", "database": str(exc.__class__.__name__)}
    return {"status": "ready", "database": "ok"}


@app.get("/api/tickets", response_model=list[schemas.TicketOut], tags=["tickets"])
def list_tickets(
    status: Optional[schemas.Status] = Query(default=None),
    priority: Optional[schemas.Priority] = Query(default=None),
    db: Session = Depends(get_db),
):
    stmt = select(models.Ticket)
    if status:
        stmt = stmt.where(models.Ticket.status == status)
    if priority:
        stmt = stmt.where(models.Ticket.priority == priority)
    return db.scalars(stmt.order_by(models.Ticket.created_at.desc(), models.Ticket.id.desc())).all()


@app.get("/api/tickets/stats", response_model=schemas.Stats, tags=["tickets"])
def ticket_stats(db: Session = Depends(get_db)):
    by_status = {s: 0 for s in models.STATUSES}
    for status, n in db.execute(select(models.Ticket.status, func.count()).group_by(models.Ticket.status)):
        by_status[status] = n
    by_priority = {p: 0 for p in models.PRIORITIES}
    for priority, n in db.execute(select(models.Ticket.priority, func.count()).group_by(models.Ticket.priority)):
        by_priority[priority] = n
    open_urgent = db.scalar(
        select(func.count()).select_from(models.Ticket).where(models.Ticket.priority == "urgent", models.Ticket.status.in_(("open", "in_progress")))
    )
    unassigned = db.scalar(select(func.count()).select_from(models.Ticket).where(models.Ticket.assignee == "", models.Ticket.status != "closed"))
    return schemas.Stats(total=sum(by_status.values()), by_status=by_status, by_priority=by_priority, open_urgent=open_urgent, unassigned=unassigned)


@app.get("/api/tickets/{ticket_id}", response_model=schemas.TicketOut, tags=["tickets"])
def get_ticket(ticket_id: int, db: Session = Depends(get_db)):
    ticket = db.get(models.Ticket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="ticket not found")
    return ticket


@app.post("/api/tickets", response_model=schemas.TicketOut, status_code=201, tags=["tickets"])
def create_ticket(payload: schemas.TicketCreate, db: Session = Depends(get_db)):
    ticket = models.Ticket(**payload.model_dump())
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket


@app.put("/api/tickets/{ticket_id}", response_model=schemas.TicketOut, tags=["tickets"])
def update_ticket(ticket_id: int, payload: schemas.TicketUpdate, db: Session = Depends(get_db)):
    ticket = db.get(models.Ticket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="ticket not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(ticket, field, value)
    db.commit()
    db.refresh(ticket)
    return ticket


@app.delete("/api/tickets/{ticket_id}", status_code=204, tags=["tickets"])
def delete_ticket(ticket_id: int, db: Session = Depends(get_db)):
    ticket = db.get(models.Ticket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="ticket not found")
    db.delete(ticket)
    db.commit()
    return Response(status_code=204)
