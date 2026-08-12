from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./skillpeer21.db"
    jwt_secret: str = "change-me"
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 14

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
