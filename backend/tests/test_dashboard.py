from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.db.session import Base, get_db
from app.main import app
from app.models.skill import Skill, SkillIntent, UserSkill
from app.models.user import TelegramVisibility, User, UserRole

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
        public_teacher = User(
            login="teacher.public",
            display_name="Public Teacher",
            password_hash=hash_password("temporary-public"),
            role=UserRole.MEMBER,
            telegram_username="public_teacher",
            telegram_visibility=TelegramVisibility.EVERYONE,
        )
        private_teacher = User(
            login="teacher.private",
            display_name="Private Teacher",
            password_hash=hash_password("temporary-private"),
            role=UserRole.MEMBER,
            telegram_username="private_teacher",
            telegram_visibility=TelegramVisibility.ADMIN_ONLY,
        )
        db.add_all([learner, public_teacher, private_teacher])
        db.flush()

        guitar = Skill(name="Гитара", normalized_name="гитара", created_by_user_id=learner.id)
        knitting = Skill(name="Вязание", normalized_name="вязание", created_by_user_id=learner.id)
        db.add_all([guitar, knitting])
        db.flush()

        db.add_all(
            [
                UserSkill(user_id=learner.id, skill_id=guitar.id, intent=SkillIntent.LEARN),
                UserSkill(user_id=learner.id, skill_id=knitting.id, intent=SkillIntent.LEARN),
                UserSkill(user_id=public_teacher.id, skill_id=guitar.id, intent=SkillIntent.TEACH),
                UserSkill(user_id=private_teacher.id, skill_id=guitar.id, intent=SkillIntent.TEACH),
            ]
        )
        db.commit()
    yield
    app.dependency_overrides.pop(get_db, None)
    Base.metadata.drop_all(engine)


def login() -> str:
    response = client.post(
        "/api/v1/auth/login",
        json={"login": "learner", "password": "temporary-learner"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_dashboard_returns_personal_matches_and_hides_private_telegram() -> None:
    response = client.get(
        "/api/v1/dashboard",
        headers={"Authorization": f"Bearer {login()}"},
    )
    assert response.status_code == 200
    data = response.json()

    assert data["summary"]["members_count"] == 3
    assert data["summary"]["skills_count"] == 2
    assert data["summary"]["matched_learning_goals_count"] == 1

    assert len(data["matches"]) == 1
    match = data["matches"][0]
    assert match["skill_name"] == "Гитара"
    assert len(match["teachers"]) == 2

    teachers = {teacher["display_name"]: teacher for teacher in match["teachers"]}
    assert teachers["Public Teacher"]["telegram_username"] == "public_teacher"
    assert teachers["Private Teacher"]["telegram_username"] is None

    stats = {row["skill_name"]: row for row in data["skills"]}
    assert stats["Гитара"]["teachers_count"] == 2
    assert stats["Гитара"]["learners_count"] == 1
    assert stats["Вязание"]["teachers_count"] == 0
    assert stats["Вязание"]["learners_count"] == 1
