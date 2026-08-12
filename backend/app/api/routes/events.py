from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.api.deps import CurrentUser, DbSession
from app.models.event import (
    Event,
    EventParticipant,
    EventParticipantRole,
    EventStatus,
    EventTimeOption,
    EventTimeVote,
)
from app.models.kudos import Kudos
from app.models.skill import Skill, SkillIntent, UserSkill
from app.models.user import User
from app.schemas.event import (
    EventConfirmRequest,
    EventCreate,
    EventParticipantRead,
    EventRead,
    EventTimeOptionRead,
)

router = APIRouter(prefix="/events", tags=["events"])


def _event_read(db: DbSession, event: Event, current_user_id: int) -> EventRead:
    skill = db.get(Skill, event.skill_id)
    participant_rows = db.execute(
        select(EventParticipant, User.display_name)
        .join(User, User.id == EventParticipant.user_id)
        .where(EventParticipant.event_id == event.id)
        .order_by(EventParticipant.role.desc(), User.display_name)
    ).all()

    participant_ids = [participant.user_id for participant, _ in participant_rows]
    kudos_counts: dict[int, int] = {}
    my_kudos: set[int] = set()
    if participant_ids:
        kudos_counts = dict(
            db.execute(
                select(Kudos.recipient_id, func.count(Kudos.id))
                .where(Kudos.event_id == event.id, Kudos.recipient_id.in_(participant_ids))
                .group_by(Kudos.recipient_id)
            ).all()
        )
        my_kudos = set(
            db.scalars(
                select(Kudos.recipient_id).where(
                    Kudos.event_id == event.id,
                    Kudos.sender_id == current_user_id,
                )
            ).all()
        )

    options = list(
        db.scalars(
            select(EventTimeOption)
            .where(EventTimeOption.event_id == event.id)
            .order_by(EventTimeOption.starts_at)
        ).all()
    )
    option_ids = [option.id for option in options]
    counts: dict[int, int] = {}
    my_votes: set[int] = set()
    teacher_votes: set[int] = set()
    if option_ids:
        counts = dict(
            db.execute(
                select(EventTimeVote.time_option_id, func.count(EventTimeVote.id))
                .where(EventTimeVote.time_option_id.in_(option_ids))
                .group_by(EventTimeVote.time_option_id)
            ).all()
        )
        my_votes = set(
            db.scalars(
                select(EventTimeVote.time_option_id).where(
                    EventTimeVote.time_option_id.in_(option_ids),
                    EventTimeVote.user_id == current_user_id,
                )
            ).all()
        )
        teacher_votes = set(
            db.scalars(
                select(EventTimeVote.time_option_id).where(
                    EventTimeVote.time_option_id.in_(option_ids),
                    EventTimeVote.user_id == event.teacher_id,
                )
            ).all()
        )

    return EventRead(
        id=event.id,
        skill_id=event.skill_id,
        skill_name=skill.name if skill else "Unknown skill",
        creator_id=event.creator_id,
        teacher_id=event.teacher_id,
        title=event.title,
        description=event.description,
        status=event.status,
        confirmed_time_option_id=event.confirmed_time_option_id,
        participants=[
            EventParticipantRead(
                user_id=participant.user_id,
                display_name=name,
                role=participant.role,
                kudos_received=kudos_counts.get(participant.user_id, 0),
                kudos_given_by_me=participant.user_id in my_kudos,
            )
            for participant, name in participant_rows
        ],
        time_options=[
            EventTimeOptionRead(
                id=option.id,
                starts_at=option.starts_at,
                votes_count=counts.get(option.id, 0),
                voted_by_me=option.id in my_votes,
                teacher_voted=option.id in teacher_votes,
            )
            for option in options
        ],
        created_at=event.created_at,
    )


@router.get("", response_model=list[EventRead])
def list_events(user: CurrentUser, db: DbSession) -> list[EventRead]:
    events = list(
        db.scalars(
            select(Event)
            .where(Event.status != EventStatus.CANCELLED)
            .order_by(Event.created_at.desc())
        ).all()
    )
    return [_event_read(db, event, user.id) for event in events]


@router.get("/{event_id}", response_model=EventRead)
def get_event(event_id: int, user: CurrentUser, db: DbSession) -> EventRead:
    event = db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    return _event_read(db, event, user.id)


@router.post("", response_model=EventRead, status_code=status.HTTP_201_CREATED)
def create_event(payload: EventCreate, user: CurrentUser, db: DbSession) -> EventRead:
    skill = db.get(Skill, payload.skill_id)
    teacher = db.get(User, payload.teacher_id)
    if skill is None or teacher is None or not teacher.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill or teacher not found")

    can_teach = db.scalar(
        select(UserSkill.id).where(
            UserSkill.user_id == teacher.id,
            UserSkill.skill_id == skill.id,
            UserSkill.intent == SkillIntent.TEACH,
        )
    )
    if can_teach is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Selected teacher does not teach this skill",
        )

    now = datetime.now(UTC)
    if any(value <= now for value in payload.time_options):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Time options must be in the future",
        )

    event = Event(
        creator_id=user.id,
        teacher_id=teacher.id,
        skill_id=skill.id,
        title=payload.title.strip(),
        description=payload.description.strip() if payload.description else None,
    )
    db.add(event)
    db.flush()

    db.add(EventParticipant(event_id=event.id, user_id=teacher.id, role=EventParticipantRole.TEACHER))
    if user.id != teacher.id:
        db.add(EventParticipant(event_id=event.id, user_id=user.id, role=EventParticipantRole.LEARNER))
    db.add_all(
        [EventTimeOption(event_id=event.id, starts_at=starts_at) for starts_at in payload.time_options]
    )
    db.commit()
    db.refresh(event)
    return _event_read(db, event, user.id)


@router.post("/{event_id}/join", response_model=EventRead)
def join_event(event_id: int, user: CurrentUser, db: DbSession) -> EventRead:
    event = db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    if event.status != EventStatus.SCHEDULING:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Event is no longer accepting participants")
    db.add(EventParticipant(event_id=event.id, user_id=user.id, role=EventParticipantRole.LEARNER))
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already participating") from exc
    return _event_read(db, event, user.id)


@router.post("/{event_id}/time-options/{time_option_id}/vote", response_model=EventRead)
def vote_time(event_id: int, time_option_id: int, user: CurrentUser, db: DbSession) -> EventRead:
    event = db.get(Event, event_id)
    option = db.get(EventTimeOption, time_option_id)
    if event is None or option is None or option.event_id != event.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event or time option not found")
    participant = db.scalar(
        select(EventParticipant.id).where(
            EventParticipant.event_id == event.id,
            EventParticipant.user_id == user.id,
        )
    )
    if participant is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Join the event before voting")
    if event.status != EventStatus.SCHEDULING:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Voting is closed")

    existing = db.scalar(
        select(EventTimeVote).where(
            EventTimeVote.time_option_id == option.id,
            EventTimeVote.user_id == user.id,
        )
    )
    if existing:
        db.delete(existing)
    else:
        db.add(EventTimeVote(time_option_id=option.id, user_id=user.id))
    db.commit()
    return _event_read(db, event, user.id)


@router.post("/{event_id}/confirm", response_model=EventRead)
def confirm_event(
    event_id: int,
    payload: EventConfirmRequest,
    user: CurrentUser,
    db: DbSession,
) -> EventRead:
    event = db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    if event.creator_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the creator can confirm the time")
    option = db.get(EventTimeOption, payload.time_option_id)
    if option is None or option.event_id != event.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Time option not found")
    teacher_vote = db.scalar(
        select(EventTimeVote.id).where(
            EventTimeVote.time_option_id == option.id,
            EventTimeVote.user_id == event.teacher_id,
        )
    )
    if teacher_vote is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Teacher must be available for the selected time",
        )
    event.confirmed_time_option_id = option.id
    event.status = EventStatus.CONFIRMED
    db.commit()
    db.refresh(event)
    return _event_read(db, event, user.id)


@router.post("/{event_id}/complete", response_model=EventRead)
def complete_event(event_id: int, user: CurrentUser, db: DbSession) -> EventRead:
    event = db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    if event.creator_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the creator can complete the event")
    if event.status != EventStatus.CONFIRMED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only a confirmed event can be completed",
        )
    event.status = EventStatus.COMPLETED
    db.commit()
    db.refresh(event)
    return _event_read(db, event, user.id)


@router.post("/{event_id}/kudos/{recipient_id}", response_model=EventRead)
def give_kudos(
    event_id: int,
    recipient_id: int,
    user: CurrentUser,
    db: DbSession,
) -> EventRead:
    event = db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    if event.status != EventStatus.COMPLETED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Kudos are available after completion")
    if recipient_id == user.id:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="You cannot give kudos to yourself")

    sender_participant = db.scalar(
        select(EventParticipant.id).where(
            EventParticipant.event_id == event.id,
            EventParticipant.user_id == user.id,
        )
    )
    recipient_participant = db.scalar(
        select(EventParticipant.id).where(
            EventParticipant.event_id == event.id,
            EventParticipant.user_id == recipient_id,
        )
    )
    if sender_participant is None or recipient_participant is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Kudos can only be exchanged between event participants",
        )

    db.add(Kudos(event_id=event.id, sender_id=user.id, recipient_id=recipient_id))
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Kudos already given") from exc
    return _event_read(db, event, user.id)


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_event(event_id: int, user: CurrentUser, db: DbSession) -> Response:
    event = db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    if event.creator_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the creator can cancel the event")
    if event.status == EventStatus.COMPLETED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Completed event cannot be cancelled")
    event.status = EventStatus.CANCELLED
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
