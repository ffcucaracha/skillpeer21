from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.user import TelegramVisibility, UserRole


class TelegramMixin(BaseModel):
    telegram_username: str | None = Field(default=None, max_length=64)

    @field_validator("telegram_username")
    @classmethod
    def normalize_telegram(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        return value.strip().removeprefix("@")


class UserCreate(TelegramMixin):
    login: str = Field(min_length=3, max_length=64, pattern=r"^[A-Za-z0-9_.-]+$")
    display_name: str | None = Field(default=None, max_length=120)
    temporary_password: str = Field(min_length=10, max_length=128)
    role: UserRole = UserRole.MEMBER
    telegram_visibility: TelegramVisibility = TelegramVisibility.ADMIN_ONLY

    @field_validator("display_name")
    @classmethod
    def normalize_display_name(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        return value.strip()


class UserProfileUpdate(TelegramMixin):
    display_name: str | None = Field(default=None, max_length=120)
    telegram_visibility: TelegramVisibility

    @field_validator("display_name")
    @classmethod
    def normalize_display_name(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        return value.strip()


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    login: str
    display_name: str
    role: UserRole
    is_active: bool
    must_change_password: bool
    telegram_username: str | None
    telegram_visibility: TelegramVisibility


class LoginRequest(BaseModel):
    login: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=10, max_length=128)
