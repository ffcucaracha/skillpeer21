from datetime import datetime

from pydantic import BaseModel, Field, model_validator

from app.models.event import EventParticipantRole, EventStatus


class EventCreate(BaseModel):
    skill_id: int
    teacher_id: int
    title: str = Field(min_length=3, max_length=160)
    description: str | None = Field(default=None, max_length=2000)
    time_options: list[datetime] = Field(min_length=2, max_length=8)

    @model_validator(mode="after")
    def unique_time_options(self) -> "EventCreate":
        if len(set(self.time_options)) != len(self.time_options):
            raise ValueError("Time options must be unique")
        return self


class EventParticipantRead(BaseModel):
    user_id: int
    display_name: str
    role: EventParticipantRole
    kudos_received: int = 0
    kudos_given_by_me: bool = False


class EventTimeOptionRead(BaseModel):
    id: int
    starts_at: datetime
    votes_count: int
    voted_by_me: bool
    teacher_voted: bool


class EventRead(BaseModel):
    id: int
    skill_id: int
    skill_name: str
    creator_id: int
    teacher_id: int
    title: str
    description: str | None
    status: EventStatus
    confirmed_time_option_id: int | None
    participants: list[EventParticipantRead]
    time_options: list[EventTimeOptionRead]
    created_at: datetime


class EventConfirmRequest(BaseModel):
    time_option_id: int
