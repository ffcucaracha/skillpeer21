from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
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


@pytest.fixture(autouse=True)
def database() -> Generator[None, None, None]:
    Base.metadata.create_all(engine)
    with TestingSession() as db:
        db.add_all(
            [
                User(
                    login="admin",
                    display_name="Administrator",
                    password_hash=hash_password("temporary-admin"),
                    role=UserRole.ADMIN,
                ),
                User(
                    login="member",
                    display_name="Member",
                    password_hash=hash_password("temporary-member"),
                    role=UserRole.MEMBER,
                ),
            ]
        )
        db.commit()
    yield
    Base.metadata.drop_all(engine)


def override_db() -> Generator[Session, None, None]:
    with TestingSession() as session:
        yield session


app.dependency_overrides[get_db] = override_db
client = TestClient(app)


def token(login: str, password: str) -> str:
    response = client.post("/api/v1/auth/login", json={"login": login, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]


def auth(value: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {value}"}


def test_member_can_create_and_link_skill() -> None:
    member_token = token("member", "temporary-member")

    created = client.post(
        "/api/v1/skills",
        headers=auth(member_token),
        json={"name": "  Игра   на гитаре  "},
    )
    assert created.status_code == 201
    assert created.json()["name"] == "Игра на гитаре"
    skill_id = created.json()["id"]

    linked = client.post(
        f"/api/v1/skills/{skill_id}/links",
        headers=auth(member_token),
        json={"intent": "learn"},
    )
    assert linked.status_code == 201
    assert linked.json()["intent"] == "learn"
    assert linked.json()["skill_name"] == "Игра на гитаре"

    mine = client.get("/api/v1/skills/me", headers=auth(member_token))
    assert mine.status_code == 200
    assert mine.json() == [linked.json()]


def test_normalized_duplicate_skill_is_rejected() -> None:
    member_token = token("member", "temporary-member")
    first = client.post(
        "/api/v1/skills",
        headers=auth(member_token),
        json={"name": "Python"},
    )
    assert first.status_code == 201

    duplicate = client.post(
        "/api/v1/skills",
        headers=auth(member_token),
        json={"name": "  python  "},
    )
    assert duplicate.status_code == 409


def test_only_admin_can_merge_skills_and_links_are_repointed() -> None:
    member_token = token("member", "temporary-member")
    admin_token = token("admin", "temporary-admin")

    source = client.post(
        "/api/v1/skills",
        headers=auth(member_token),
        json={"name": "Guitar"},
    ).json()
    target = client.post(
        "/api/v1/skills",
        headers=auth(member_token),
        json={"name": "Игра на гитаре"},
    ).json()

    client.post(
        f"/api/v1/skills/{source['id']}/links",
        headers=auth(member_token),
        json={"intent": "learn"},
    )
    client.post(
        f"/api/v1/skills/{target['id']}/links",
        headers=auth(member_token),
        json={"intent": "learn"},
    )

    denied = client.post(
        f"/api/v1/skills/{source['id']}/merge",
        headers=auth(member_token),
        json={"target_skill_id": target["id"]},
    )
    assert denied.status_code == 403

    merged = client.post(
        f"/api/v1/skills/{source['id']}/merge",
        headers=auth(admin_token),
        json={"target_skill_id": target["id"]},
    )
    assert merged.status_code == 200
    assert merged.json()["id"] == target["id"]

    with TestingSession() as db:
        assert db.get(Skill, source["id"]) is None
        links = list(db.scalars(select(UserSkill).where(UserSkill.intent == SkillIntent.LEARN)).all())
        assert len(links) == 1
        assert links[0].skill_id == target["id"]
