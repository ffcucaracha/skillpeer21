from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.db.session import Base, get_db
from app.main import app
from app.models.event import Event, EventParticipant, EventParticipantRole
from app.models.kudos import Kudos
from app.models.skill import Skill
from app.models.user import User, UserRole

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSession = sessionmaker(bind=engine, expire_on_commit=False)
client = TestClient(app)


def override_db() -> Generator[Session, None, None]:
    with TestingSession() as session:
        yield session


@pytest.fixture(autouse=True)
def database() -> Generator[None, None, None]:
    Base.metadata.create_all(engine)
    app.dependency_overrides[get_db] = override_db
    with TestingSession() as db:
        admin = User(
            login="admin",
            display_name="Administrator",
            password_hash=hash_password("temporary-admin"),
            role=UserRole.ADMIN,
        )
        member = User(
            login="member",
            display_name="Member",
            password_hash=hash_password("temporary-member"),
            role=UserRole.MEMBER,
        )
        teacher = User(
            login="teacher",
            display_name="Teacher",
            password_hash=hash_password("temporary-teacher"),
            role=UserRole.MEMBER,
        )
        db.add_all([admin, member, teacher])
        db.flush()
        skill = Skill(name="Python", normalized_name="python", created_by_user_id=member.id)
        db.add(skill)
        db.flush()
        event = Event(
            creator_id=member.id,
            teacher_id=teacher.id,
            skill_id=skill.id,
            title="Python meetup",
        )
        db.add(event)
        db.flush()
        db.add_all(
            [
                EventParticipant(event_id=event.id, user_id=member.id, role=EventParticipantRole.LEARNER),
                EventParticipant(event_id=event.id, user_id=teacher.id, role=EventParticipantRole.TEACHER),
                Kudos(event_id=event.id, sender_id=member.id, recipient_id=teacher.id),
            ]
        )
        db.commit()
    yield
    app.dependency_overrides.pop(get_db, None)
    Base.metadata.drop_all(engine)


def token(login: str, password: str) -> str:
    response = client.post("/api/v1/auth/login", json={"login": login, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]


def auth(value: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {value}"}


def test_admin_summary_and_events_are_admin_only() -> None:
    admin_token = token("admin", "temporary-admin")
    member_token = token("member", "temporary-member")

    denied = client.get("/api/v1/admin/summary", headers=auth(member_token))
    assert denied.status_code == 403

    summary = client.get("/api/v1/admin/summary", headers=auth(admin_token))
    assert summary.status_code == 200
    assert summary.json() == {
        "users_total": 3,
        "users_active": 3,
        "skills_total": 1,
        "events_total": 1,
        "events_scheduling": 1,
        "events_confirmed": 0,
        "events_completed": 0,
        "kudos_total": 1,
    }

    events = client.get("/api/v1/admin/events", headers=auth(admin_token))
    assert events.status_code == 200
    assert events.json()[0]["participants_count"] == 2
    assert events.json()[0]["skill_name"] == "Python"


def test_admin_can_deactivate_member_and_cancel_event() -> None:
    admin_token = token("admin", "temporary-admin")
    with TestingSession() as db:
        member = db.query(User).filter_by(login="member").one()
        member_id = member.id
        event_id = db.query(Event).one().id

    updated = client.patch(
        f"/api/v1/admin/users/{member_id}",
        headers=auth(admin_token),
        json={"is_active": False},
    )
    assert updated.status_code == 200
    assert updated.json()["is_active"] is False

    cancelled = client.post(f"/api/v1/admin/events/{event_id}/cancel", headers=auth(admin_token))
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"


def test_admin_cannot_deactivate_self() -> None:
    admin_token = token("admin", "temporary-admin")
    with TestingSession() as db:
        admin_id = db.query(User).filter_by(login="admin").one().id

    response = client.patch(
        f"/api/v1/admin/users/{admin_id}",
        headers=auth(admin_token),
        json={"is_active": False},
    )
    assert response.status_code == 422
