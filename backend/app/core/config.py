"""Application configuration loaded from environment and .env."""

import logging
import os
import secrets
from typing import Literal, Self, cast

from pydantic import BaseModel, Field, computed_field, field_validator, model_validator

from app.core._env import load_env_file

# Apply the .env file before any field defaults are evaluated — process env
# wins (setdefault inside load_env_file).
load_env_file(os.environ.get("ORBVIS_ENV_FILE", ".env"))

logger = logging.getLogger(__name__)


def _env_str(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


def _env_bool(key: str, default: bool = False) -> bool:
    raw = os.environ.get(key)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _env_int(key: str, default: int) -> int:
    raw = os.environ.get(key)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_float(key: str, default: float) -> float:
    raw = os.environ.get(key)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _env_list(key: str, default: list[str]) -> list[str]:
    raw = os.environ.get(key)
    if raw is None:
        return list(default)
    return [item.strip() for item in raw.split(",") if item.strip()]


class Settings(BaseModel):
    app_name: str = Field(default_factory=lambda: _env_str("APP_NAME", "OrbVis"))
    debug: bool = Field(default_factory=lambda: _env_bool("DEBUG", False))
    environment: Literal["development", "production", "testing"] = Field(
        default_factory=lambda: _env_str("ENVIRONMENT", "production")  # type: ignore[arg-type]
    )
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] | None = Field(
        default_factory=lambda: cast(
            Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] | None,
            _env_str("LOG_LEVEL") or None,
        )
    )

    database_url: str = Field(
        default_factory=lambda: _env_str("DATABASE_URL", "sqlite:///./orbvis.db")
    )

    secret_key: str = Field(default_factory=lambda: _env_str("SECRET_KEY", ""))
    algorithm: str = Field(default_factory=lambda: _env_str("ALGORITHM", "HS256"))
    access_token_expire_minutes: int = Field(
        default_factory=lambda: _env_int("ACCESS_TOKEN_EXPIRE_MINUTES", 60)
    )
    refresh_token_expire_days: int = Field(
        default_factory=lambda: _env_int("REFRESH_TOKEN_EXPIRE_DAYS", 30)
    )

    checkmk_htpasswd: str = Field(default_factory=lambda: _env_str("CHECKMK_HTPASSWD"))
    checkmk_omd_root: str = Field(default_factory=lambda: _env_str("CHECKMK_OMD_ROOT"))
    checkmk_site: str = Field(default_factory=lambda: _env_str("CHECKMK_SITE"))

    boards_dir: str = Field(default_factory=lambda: _env_str("BOARDS_DIR", "./boards"))
    connections_file: str = Field(
        default_factory=lambda: _env_str("CONNECTIONS_FILE", "./connections.json")
    )

    ws_ping_interval: int = Field(default_factory=lambda: _env_int("WS_PING_INTERVAL", 30))
    state_refresh_interval: int = Field(
        default_factory=lambda: _env_int("STATE_REFRESH_INTERVAL", 5)
    )
    # Cold-start livestatus calls on busy 500+ host sites can exceed the original
    # 10 s budget; 30 s keeps fan/orbit/row usable while still guarding against
    # truly stuck sockets.
    connection_query_timeout: int = Field(
        default_factory=lambda: _env_int("CONNECTION_QUERY_TIMEOUT", 30)
    )
    connection_pool_size: int = Field(default_factory=lambda: _env_int("CONNECTION_POOL_SIZE", 20))

    flow_board_max_services_per_host: int = Field(
        default_factory=lambda: _env_int("FLOW_BOARD_MAX_SERVICES_PER_HOST", 50)
    )
    flow_board_topology_cache_ttl: float = Field(
        default_factory=lambda: _env_float("FLOW_BOARD_TOPOLOGY_CACHE_TTL", 20.0)
    )
    # Mirror cmk.gui.nodevis: only fetch service detail for the top-K hosts
    # ranked by problem count. 25 keeps the OR-filter against the services
    # table cheap on multi-hundred-host installations.
    flow_board_top_affected_hosts: int = Field(
        default_factory=lambda: _env_int("FLOW_BOARD_TOP_AFFECTED_HOSTS", 25)
    )

    flow_board_bulk_service_chunk_size: int = Field(
        default_factory=lambda: _env_int("FLOW_BOARD_BULK_SERVICE_CHUNK_SIZE", 5), ge=1
    )

    # Cap parallel chunks per Livestatus connection: each chunk opens its own
    # socket; firing 100+ in parallel exhausts the unix-socket listen backlog
    # (BlockingIOError: [Errno 11] Resource temporarily unavailable). 8 stays
    # below the kernel's default backlog (128) and below connection_pool_size.
    flow_board_bulk_max_concurrent_chunks: int = Field(
        default_factory=lambda: _env_int("FLOW_BOARD_BULK_MAX_CONCURRENT_CHUNKS", 8),
        ge=1,
        le=64,
    )

    connection_warmup_interval: int = Field(
        default_factory=lambda: _env_int("CONNECTION_WARMUP_INTERVAL", 60)
    )

    # Hard cap on object-name autocomplete results (host/group pickers in the
    # board editor). Without it a multi-million-host site would stream every
    # name into a config dropdown and freeze the UI. The editor filters the
    # returned set client-side; a truncation hint is logged + surfaced.
    object_autocomplete_limit: int = Field(
        default_factory=lambda: _env_int("OBJECT_AUTOCOMPLETE_LIMIT", 5000), ge=1
    )

    allowed_origins: list[str] = Field(
        default_factory=lambda: _env_list(
            "ALLOWED_ORIGINS", ["http://localhost:3000", "http://localhost:5173"]
        )
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def sync_database_url(self) -> str:
        return self.database_url.replace("+aiosqlite", "")

    @model_validator(mode="after")
    def _ensure_secret_key(self) -> Self:
        if self.secret_key:
            return self
        if self.environment == "production":
            # Never fall back silently in production: a server started without
            # a persistent SECRET_KEY invalidates every JWT on restart and is
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
