"""Stdlib sqlite3 wrapper — replaces SQLAlchemy + aiosqlite + alembic.

Schema lives in core/schema.sql, applied idempotently at startup. Service-layer
queries are wrapped in ``asyncio.to_thread`` (via ``db_run``) so the async
surface to FastAPI handlers stays the same.
"""

from __future__ import annotations

import asyncio
import logging
import sqlite3
from collections.abc import AsyncGenerator, Callable
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger(__name__)

_SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def _resolve_db_path() -> str:
    # Accept the legacy SQLAlchemy URL forms so on-disk databases from the
    # previous setup keep working without operator action.
    url = settings.database_url
    for prefix in ("sqlite+aiosqlite://", "sqlite+pysqlite://", "sqlite://"):
        if url.startswith(prefix):
            url = url[len(prefix) :]
            break
    if url.startswith("/"):
        url = url[1:]
    return url or ":memory:"


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(
        _resolve_db_path(),
        # FastAPI yields the connection to threadpool workers via db_run.
        check_same_thread=False,
        # autocommit; explicit BEGIN/COMMIT where transactionality matters.
        isolation_level=None,
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


async def get_db() -> AsyncGenerator[sqlite3.Connection, None]:
    conn = _connect()
    try:
        yield conn
    finally:
        conn.close()


async def db_run[**P, T](fn: Callable[P, T], /, *args: P.args, **kwargs: P.kwargs) -> T:
    return await asyncio.to_thread(fn, *args, **kwargs)


def _ensure_schema() -> None:
    # Drop the legacy alembic_version table so on-disk layout converges with
    # fresh installs after the alembic dependency is gone.
    conn = _connect()
    try:
        conn.executescript(_SCHEMA_PATH.read_text())
        conn.execute("DROP TABLE IF EXISTS alembic_version")
    finally:
        conn.close()
    logger.info("Database schema ensured (%s)", _resolve_db_path())
