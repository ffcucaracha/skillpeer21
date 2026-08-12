import jwt
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.core.security import create_token, decode_token, hash_password, verify_password
from app.models.user import User
from app.schemas.user import (
    ChangePasswordRequest,
    LoginRequest,
    RefreshRequest,
    TokenPair,
    UserProfileUpdate,
    UserRead,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _tokens(user: User) -> TokenPair:
    return TokenPair(
        access_token=create_token(
            user_id=user.id,
            role=user.role.value,
            token_version=user.token_version,
            token_type="access",
        ),
        refresh_token=create_token(
            user_id=user.id,
            role=user.role.value,
            token_version=user.token_version,
            token_type="refresh",
        ),
    )


@router.post("/login", response_model=TokenPair)
def login(payload: LoginRequest, db: DbSession) -> TokenPair:
    user = db.scalar(select(User).where(User.login == payload.login))
    if user is None or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return _tokens(user)


@router.post("/refresh", response_model=TokenPair)
def refresh(payload: RefreshRequest, db: DbSession) -> TokenPair:
    try:
        claims = decode_token(payload.refresh_token)
        if claims.get("type") != "refresh":
            raise ValueError("wrong token type")
        user = db.get(User, int(claims["sub"]))
    except (jwt.InvalidTokenError, KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token") from exc
    if user is None or not user.is_active or claims.get("ver") != user.token_version:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    return _tokens(user)


@router.get("/me", response_model=UserRead)
def me(user: CurrentUser) -> User:
    return user


@router.patch("/me", response_model=UserRead)
def update_me(payload: UserProfileUpdate, user: CurrentUser, db: DbSession) -> User:
    user.display_name = payload.display_name or user.login
    user.telegram_username = payload.telegram_username
    user.telegram_visibility = payload.telegram_visibility
    db.commit()
    db.refresh(user)
    return user


@router.post("/change-password", response_model=TokenPair)
def change_password(payload: ChangePasswordRequest, user: CurrentUser, db: DbSession) -> TokenPair:
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")
    user.password_hash = hash_password(payload.new_password)
    user.must_change_password = False
    user.token_version += 1
    db.commit()
    db.refresh(user)
    return _tokens(user)
