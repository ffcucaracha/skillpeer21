from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.db.session import Base, get_db
from app.main import app
from app.models.user import User, UserRole

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSession = sessionmaker(bind=engine, expire_on_commit=False)


def override_db() -> Generator[Session, None, None]:
    with TestingSession() as session:
        yield session


@pytest.fixture(autouse=True)
def database() -> Generator[None, None, None]:
    app.dependency_overrides[get_db] = override_db
    Base.metadata.create_all(engine)
    with TestingSession() as db:
        db.add(
            User(
                login="admin",
                display_name="Administrator",
                password_hash=hash_password("temporary-admin"),
                role=UserRole.ADMIN,
            )
        )
        db.commit()
    yield
    app.dependency_overrides.pop(get_db, None)
    Base.metadata.drop_all(engine)


client = TestClient(app)


def login(login: str, password: str) -> dict[str, str]:
    response = client.post("/api/v1/auth/login", json={"login": login, "password": password})
    assert response.status_code == 200
    return response.json()


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_admin_can_create_member_and_member_cannot_create_users() -> None:
    admin_tokens = login("admin", "temporary-admin")
    create = client.post(
        "/api/v1/users",
        headers=auth_header(admin_tokens["access_token"]),
        json={
            "login": "member.one",
            "display_name": "Member One",
            "temporary_password": "temporary-member",
        },
    )
    assert create.status_code == 201
    assert create.json()["must_change_password"] is True
    assert create.json()["role"] == "member"

    member_tokens = login("member.one", "temporary-member")
    denied = client.post(
        "/api/v1/users",
        headers=auth_header(member_tokens["access_token"]),
        json={
            "login": "member.two",
            "display_name": "Member Two",
            "temporary_password": "another-password",
        },
    )
    assert denied.status_code == 403


def test_change_password_invalidates_old_token_and_returns_new_pair() -> None:
    tokens = login("admin", "temporary-admin")
    changed = client.post(
        "/api/v1/auth/change-password",
        headers=auth_header(tokens["access_token"]),
        json={"current_password": "temporary-admin", "new_password": "new-secure-password"},
    )
    assert changed.status_code == 200
    new_tokens = changed.json()

    old_me = client.get("/api/v1/auth/me", headers=auth_header(tokens["access_token"]))
    assert old_me.status_code == 401

    new_me = client.get("/api/v1/auth/me", headers=auth_header(new_tokens["access_token"]))
    assert new_me.status_code == 200
    assert new_me.json()["must_change_password"] is False


def test_refresh_token_cannot_be_used_as_access_token() -> None:
    tokens = login("admin", "temporary-admin")
    response = client.get("/api/v1/auth/me", headers=auth_header(tokens["refresh_token"]))
    assert response.status_code == 401
