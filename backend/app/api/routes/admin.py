from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select

from app.api.deps import AdminUser, DbSession
from app.models.event import Event, EventParticipant, EventStatus
from app.models.kudos import Kudos
from app.models.skill import Skill
from app.models.user import User
from app.schemas.admin import AdminEventRead, AdminSummary, AdminUserUpdate
from app.schemas.user import UserRead

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/summary", response_model=AdminSummary)
def admin_summary(_admin: AdminUser, db: DbSession) -> AdminSummary:
    return AdminSummary(
        users_total=db.scalar(select(func.count(User.id))) or 0,
        users_active=db.scalar(select(func.count(User.id)).where(User.is_active.is_(True))) or 0,
        skills_total=db.scalar(select(func.count(Skill.id))) or 0,
        events_total=db.scalar(select(func.count(Event.id))) or 0,
        events_scheduling=db.scalar(
            select(func.count(Event.id)).where(Event.status == EventStatus.SCHEDULING)
        )
        or 0,
        events_confirmed=db.scalar(
            select(func.count(Event.id)).where(Event.status == EventStatus.CONFIRMED)
        )
        or 0,
        events_completed=db.scalar(
            select(func.count(Event.id)).where(Event.status == EventStatus.COMPLETED)
        )
        or 0,
        kudos_total=db.scalar(select(func.count(Kudos.id))) or 0,
    )


@router.patch("/users/{user_id}", response_model=UserRead)
def update_user(
    user_id: int,
    payload: AdminUserUpdate,
    admin: AdminUser,
    db: DbSession,
) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.id == admin.id and payload.is_active is False:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Administrator cannot deactivate their own account",
        )
    if payload.is_active is not None:
        user.is_active = payload.is_active
        if not payload.is_active:
            user.token_version += 1
    if payload.role is not None:
        user.role = payload.role
    db.commit()
    db.refresh(user)
    return user


@router.get("/events", response_model=list[AdminEventRead])
def admin_events(_admin: AdminUser, db: DbSession) -> list[AdminEventRead]:
    creator = User.__table__.alias("creator")
    teacher = User.__table__.alias("teacher")
    participant_counts = (
        select(EventParticipant.event_id, func.count(EventParticipant.id).label("participants_count"))
        .group_by(EventParticipant.event_id)
        .subquery()
    )
    rows = db.execute(
        select(
            Event,
            Skill.name,
            creator.c.display_name,
            teacher.c.display_name,
            func.coalesce(participant_counts.c.participants_count, 0),
        )
        .join(Skill, Skill.id == Event.skill_id)
        .join(creator, creator.c.id == Event.creator_id)
        .join(teacher, teacher.c.id == Event.teacher_id)
        .outerjoin(participant_counts, participant_counts.c.event_id == Event.id)
        .order_by(Event.created_at.desc())
    ).all()
    return [
        AdminEventRead(
            id=event.id,
            title=event.title,
            skill_name=skill_name,
            creator_name=creator_name,
            teacher_name=teacher_name,
            status=event.status,
            participants_count=participants_count,
            created_at=event.created_at,
        )
        for event, skill_name, creator_name, teacher_name, participants_count in rows
    ]


@router.post("/events/{event_id}/cancel", response_model=AdminEventRead)
def admin_cancel_event(event_id: int, _admin: AdminUser, db: DbSession) -> AdminEventRead:
    event = db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    if event.status == EventStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Completed event cannot be cancelled",
        )
    event.status = EventStatus.CANCELLED
    db.commit()

    skill = db.get(Skill, event.skill_id)
    creator = db.get(User, event.creator_id)
    teacher = db.get(User, event.teacher_id)
    participants_count = db.scalar(
        select(func.count(EventParticipant.id)).where(EventParticipant.event_id == event.id)
    ) or 0
    return AdminEventRead(
        id=event.id,
        title=event.title,
        skill_name=skill.name if skill else "Unknown skill",
        creator_name=creator.display_name if creator else "Unknown user",
        teacher_name=teacher.display_name if teacher else "Unknown user",
        status=event.status,
        participants_count=participants_count,
        created_at=event.created_at,
    )
