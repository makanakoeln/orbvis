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

    app_name: str = "OrbVis"
    debug: bool = False
    environment: Literal["development", "production", "testing"] = "production"
    # Overrides the debug flag when explicitly set. Standard Python logging names.
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] | None = None

    database_url: str = "sqlite+aiosqlite:///./orbvis.db"

    # Required in production: see _ensure_secret_key validator below.
    secret_key: str = ""
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 30

    checkmk_htpasswd: str = ""
    checkmk_omd_root: str = ""
    checkmk_site: str = ""

    boards_dir: str = "./boards"
    connections_file: str = "./connections.json"

    ws_ping_interval: int = 30
    state_refresh_interval: int = 5
    connection_query_timeout: int = 10
    connection_pool_size: int = 20

    # Flow-board scaling guards: cap services per host and cache topology
    # results briefly so concurrent tabs share one Livestatus round-trip.
    flow_board_max_services_per_host: int = 50
    flow_board_topology_cache_ttl: float = 10.0
    # Mirror cmk.gui.nodevis: only fetch service detail for the top-K hosts
    # ranked by problem count (crit+warn+unknown+pending). The remaining hosts
    # render donut-only from the per-host num_services_* aggregates.
    flow_board_top_affected_hosts: int = 50

    allowed_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    # mypy's pydantic plugin doesn't model the @property-under-@computed_field
    # stacking — the "prop-decorator" error-code is a known mypy limitation, not
    # a real typing issue. Keep the ignore scoped to the exact code.
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
