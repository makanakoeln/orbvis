"""Application configuration via pydantic-settings."""

import secrets
import warnings
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # App
    app_name: str = "OrbVis"
    debug: bool = False
    environment: Literal["development", "production", "testing"] = "production"

    # Database
    database_url: str = "sqlite+aiosqlite:///./orbvis.db"

    # Security
    # Must be set via SECRET_KEY env var or .env; if unset an ephemeral key is generated
    # and all JWTs become invalid after every restart.
    secret_key: str = ""
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 30

    # Checkmk/OMD integration
    # Path to htpasswd file (fallback login with Checkmk credentials)
    checkmk_htpasswd: str = ""
    # OMD site root (e.g. /omd/sites/heute) – enables cookie-based SSO
    checkmk_omd_root: str = ""
    # OMD site name (e.g. heute) – used as auth cookie name: auth_<site>
    checkmk_site: str = ""

    # Maps
    maps_dir: str = "./maps"

    # Monitoring backends
    backends_file: str = "./backends.json"

    # WebSocket
    ws_ping_interval: int = 30
    state_refresh_interval: int = 5

    # CORS
    allowed_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    @field_validator("secret_key", mode="after")
    @classmethod
    def _ensure_secret_key(cls, v: str) -> str:
        if not v:
            warnings.warn(
                "SECRET_KEY is not set – using an ephemeral random key. "
                "All JWTs will be invalidated on every restart. "
                "Set SECRET_KEY=<hex64> in .env for production.",
                stacklevel=2,
            )
            return secrets.token_hex(32)
        return v

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_origins(cls, v: str | list) -> list[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v


settings = Settings()
