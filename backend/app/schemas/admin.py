from datetime import datetime

from pydantic import BaseModel

from app.models.event import EventStatus
from app.models.user import UserRole


class AdminSummary(BaseModel):
    users_total: int
    users_active: int
    skills_total: int
    events_total: int
    events_scheduling: int
    events_confirmed: int
    events_completed: int
    kudos_total: int


class AdminUserUpdate(BaseModel):
    is_active: bool | None = None
    role: UserRole | None = None


class AdminEventRead(BaseModel):
    id: int
    title: str
    skill_name: str
    creator_name: str
    teacher_name: str
    status: EventStatus
    participants_count: int
    created_at: datetime
