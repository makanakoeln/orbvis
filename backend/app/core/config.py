"""Application configuration via pydantic-settings."""

import logging
import secrets
from typing import Literal, Self

from pydantic import computed_field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


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

    # Boards
    boards_dir: str = "./boards"

    # Monitoring backends
    backends_file: str = "./backends.json"

    # WebSocket
    ws_ping_interval: int = 30
    state_refresh_interval: int = 5

    # Monitoring backend limits
    backend_query_timeout: int = 10  # seconds; caps full round-trip per LQL query
    backend_max_connections: int = 20  # max concurrent Livestatus socket connections

    # CORS
    allowed_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def sync_database_url(self) -> str:
        return self.database_url.replace("+aiosqlite", "").replace("+asyncpg", "")

    @model_validator(mode="after")
    def _ensure_secret_key(self) -> Self:
        if self.secret_key:
            return self
        if self.environment == "production":
            # Never fall back silently in production. A server started without a
            # persistent SECRET_KEY will invalidate every JWT on restart and is
            # trivially rotatable by any crash-loop attacker.
            raise ValueError(
                "SECRET_KEY is required in production. "
                "Set SECRET_KEY=<hex64> (e.g. `openssl rand -hex 32`) in the environment."
            )
        logger.warning(
            "SECRET_KEY is not set — using an ephemeral random key (env=%s). "
            "All JWTs will be invalidated on every restart. "
            "Set SECRET_KEY=<hex64> in .env for a stable key.",
            self.environment,
        )
        self.secret_key = secrets.token_hex(32)
        return self

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v


settings = Settings()
