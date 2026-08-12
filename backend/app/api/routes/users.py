from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.deps import AdminUser, DbSession
from app.core.security import hash_password
from app.models.user import User
from app.schemas.user import UserCreate, UserRead

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, _admin: AdminUser, db: DbSession) -> User:
    user = User(
        login=payload.login,
        display_name=payload.display_name,
        password_hash=hash_password(payload.temporary_password),
        role=payload.role,
        telegram_username=payload.telegram_username,
        telegram_visibility=payload.telegram_visibility,
        must_change_password=True,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Login already exists") from exc
    db.refresh(user)
    return user


@router.get("", response_model=list[UserRead])
def list_users(_admin: AdminUser, db: DbSession) -> list[User]:
    return list(db.scalars(select(User).order_by(User.display_name, User.id)).all())
