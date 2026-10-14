from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="APP_", env_file=".env", extra="ignore")

    name: str = "Resume Tailor"
    mode: Literal["local", "server"] = "local"
    database_url: str = "sqlite:///./resume-tailor.db"
    frontend_origins: list[str] = [
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:8080",
        "http://localhost:8080",
    ]
    api_host: str = "127.0.0.1"
    api_port: int = Field(default=8000, ge=1, le=65535)
    llm_base_url: str = "http://127.0.0.1:1234/v1"

    @field_validator("database_url")
    @classmethod
    def supported_database(cls, value: str) -> str:
        if make_url(value).drivername not in {"sqlite", "postgresql+psycopg"}:
            raise ValueError("Use sqlite or postgresql+psycopg")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
