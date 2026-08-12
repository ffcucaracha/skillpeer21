from collections.abc import Generator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.db.session import Base, get_db
from app.main import app
from app.models.skill import Skill, SkillIntent, UserSkill
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
        learner = User(
            login="learner",
            display_name="Learner",
            password_hash=hash_password("temporary-learner"),
            role=UserRole.MEMBER,
        )
        teacher = User(
            login="teacher",
            display_name="Teacher",
            password_hash=hash_password("temporary-teacher"),
            role=UserRole.MEMBER,
        )
        another = User(
            login="another",
            display_name="Another Learner",
            password_hash=hash_password("temporary-another"),
            role=UserRole.MEMBER,
        )
        db.add_all([learner, teacher, another])
        db.flush()
        guitar = Skill(name="Гитара", normalized_name="гитара", created_by_user_id=learner.id)
        db.add(guitar)
        db.flush()
        db.add_all(
            [
                UserSkill(user_id=learner.id, skill_id=guitar.id, intent=SkillIntent.LEARN),
                UserSkill(user_id=teacher.id, skill_id=guitar.id, intent=SkillIntent.TEACH),
                UserSkill(user_id=another.id, skill_id=guitar.id, intent=SkillIntent.LEARN),
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


def test_event_flow_requires_teacher_availability_before_confirmation() -> None:
    learner_token = token("learner", "temporary-learner")
    teacher_token = token("teacher", "temporary-teacher")
    another_token = token("another", "temporary-another")

    with TestingSession() as db:
        skill_id = db.query(Skill).filter_by(normalized_name="гитара").one().id
        teacher_id = db.query(User).filter_by(login="teacher").one().id

    first = datetime.now(UTC) + timedelta(days=1)
    second = datetime.now(UTC) + timedelta(days=2)
    created = client.post(
        "/api/v1/events",
        headers=auth(learner_token),
        json={
            "skill_id": skill_id,
            "teacher_id": teacher_id,
            "title": "Первая встреча по гитаре",
            "description": "Разберём базовые аккорды.",
            "time_options": [first.isoformat(), second.isoformat()],
        },
    )
    assert created.status_code == 201
    event = created.json()
    assert event["status"] == "scheduling"
    assert len(event["participants"]) == 2
    assert len(event["time_options"]) == 2

    event_id = event["id"]
    option_id = event["time_options"][0]["id"]

    joined = client.post(f"/api/v1/events/{event_id}/join", headers=auth(another_token))
    assert joined.status_code == 200
    assert len(joined.json()["participants"]) == 3

    learner_vote = client.post(
        f"/api/v1/events/{event_id}/time-options/{option_id}/vote",
        headers=auth(learner_token),
    )
    assert learner_vote.status_code == 200
    assert learner_vote.json()["time_options"][0]["votes_count"] == 1

    too_early = client.post(
        f"/api/v1/events/{event_id}/confirm",
        headers=auth(learner_token),
        json={"time_option_id": option_id},
    )
    assert too_early.status_code == 409

    teacher_vote = client.post(
        f"/api/v1/events/{event_id}/time-options/{option_id}/vote",
        headers=auth(teacher_token),
    )
    assert teacher_vote.status_code == 200
    assert teacher_vote.json()["time_options"][0]["teacher_voted"] is True

    confirmed = client.post(
        f"/api/v1/events/{event_id}/confirm",
        headers=auth(learner_token),
        json={"time_option_id": option_id},
    )
    assert confirmed.status_code == 200
    assert confirmed.json()["status"] == "confirmed"
    assert confirmed.json()["confirmed_time_option_id"] == option_id


def test_event_cannot_use_user_who_does_not_teach_skill() -> None:
    learner_token = token("learner", "temporary-learner")
    with TestingSession() as db:
        skill_id = db.query(Skill).filter_by(normalized_name="гитара").one().id
        wrong_teacher_id = db.query(User).filter_by(login="another").one().id

    response = client.post(
        "/api/v1/events",
        headers=auth(learner_token),
        json={
            "skill_id": skill_id,
            "teacher_id": wrong_teacher_id,
            "title": "Некорректная встреча",
            "time_options": [
                (datetime.now(UTC) + timedelta(days=1)).isoformat(),
                (datetime.now(UTC) + timedelta(days=2)).isoformat(),
            ],
        },
    )
    assert response.status_code == 422
