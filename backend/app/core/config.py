"""Application configuration via pydantic-settings."""

from typing import Literal
import secrets

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # App
    app_name: str = "NagVis 2"
    debug: bool = False
    environment: Literal["development", "production", "testing"] = "production"

    # Database
    database_url: str = "sqlite+aiosqlite:///./nagvis.db"

    # Security
    secret_key: str = secrets.token_hex(32)
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 30

    # Maps
    maps_dir: str = "./maps"

    # Monitoring backends
    default_backend_id: str = "live_1"

    # WebSocket
    ws_ping_interval: int = 30
    state_refresh_interval: int = 5

    # CORS
    allowed_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_origins(cls, v: str | list) -> list[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v


settings = Settings()
