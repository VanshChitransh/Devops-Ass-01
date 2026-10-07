from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

Priority = Literal["low", "medium", "high", "urgent"]
Status = Literal["open", "in_progress", "resolved", "closed"]


class TicketCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(default="", max_length=5000)
    priority: Priority = "medium"
    status: Status = "open"
    requester: str = Field(min_length=1, max_length=100)
    assignee: str = Field(default="", max_length=100)


class TicketUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=3, max_length=200)
    description: Optional[str] = Field(default=None, max_length=5000)
    priority: Optional[Priority] = None
    status: Optional[Status] = None
    requester: Optional[str] = Field(default=None, min_length=1, max_length=100)
    assignee: Optional[str] = Field(default=None, max_length=100)


class TicketOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    priority: str
    status: str
    requester: str
    assignee: str
    created_at: datetime
    updated_at: datetime


class Stats(BaseModel):
    total: int
    by_status: dict[str, int]
    by_priority: dict[str, int]
    open_urgent: int
    unassigned: int
