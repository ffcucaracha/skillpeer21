from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class EventStatus(StrEnum):
    SCHEDULING = "scheduling"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class EventParticipantRole(StrEnum):
    TEACHER = "teacher"
    LEARNER = "learner"


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True)
    creator_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id", ondelete="RESTRICT"), index=True)
    title: Mapped[str] = mapped_column(String(160))
    description: Mapped[str | None] = mapped_column(Text(), nullable=True)
    status: Mapped[EventStatus] = mapped_column(
        Enum(EventStatus, name="event_status"), default=EventStatus.SCHEDULING
    )
    confirmed_time_option_id: Mapped[int | None] = mapped_column(
        ForeignKey("event_time_options.id", ondelete="SET NULL", use_alter=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class EventParticipant(Base):
    __tablename__ = "event_participants"
    __table_args__ = (UniqueConstraint("event_id", "user_id", name="uq_event_participant"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    role: Mapped[EventParticipantRole] = mapped_column(
        Enum(EventParticipantRole, name="event_participant_role")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EventTimeOption(Base):
    __tablename__ = "event_time_options"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"), index=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EventTimeVote(Base):
    __tablename__ = "event_time_votes"
    __table_args__ = (
        UniqueConstraint("time_option_id", "user_id", name="uq_event_time_vote"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    time_option_id: Mapped[int] = mapped_column(
        ForeignKey("event_time_options.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
