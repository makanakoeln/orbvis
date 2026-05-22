"""Test fixtures and configuration."""

from __future__ import annotations

import os
import sqlite3
import tempfile
from pathlib import Path

# Force a testing environment + deterministic SECRET_KEY before anything imports
# app.core.config — otherwise production-mode config validation aborts the tests.
os.environ.setdefault("ENVIRONMENT", "testing")
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")

# Per-test database file — set before app.core.config reads DATABASE_URL.
_TMPDIR = Path(tempfile.mkdtemp(prefix="orbvis-test-"))
_DB_PATH = _TMPDIR / "test.db"
os.environ.setdefault("DATABASE_URL", f"sqlite:///{_DB_PATH}")

from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.connections.base import ConnectionBase
from app.core.database import _connect, _ensure_schema, get_db
from app.core.security import hash_password
from app.main import app
from app.models.user import User


@pytest.fixture(autouse=True)
def setup_db():
    if _DB_PATH.exists():
        _DB_PATH.unlink()
    _ensure_schema()
    yield
    if _DB_PATH.exists():
        _DB_PATH.unlink()


@pytest.fixture(autouse=True)
def _reset_board_cache():
    # Module-level board cache leaks between tests because tests reuse names
    # like "src-board" against different tmp_paths.
    from app.services import board_service

    def _wipe() -> None:
        for timer in board_service._FLUSH_TIMERS.values():
            timer.cancel()
        board_service._FLUSH_TIMERS.clear()
        board_service._CACHE.clear()
        board_service._DIRTY.clear()

    _wipe()
    yield
    _wipe()


@pytest.fixture
def db_session() -> sqlite3.Connection:
    """Provide a per-test sqlite3 connection (was AsyncSession pre-refactor)."""
    conn = _connect()
    try:
        yield conn
    finally:
        conn.close()


@pytest_asyncio.fixture
async def client(db_session: sqlite3.Connection):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


def _insert_user(
    conn: sqlite3.Connection,
    *,
    name: str,
    password: str,
    is_active: bool = True,
    is_admin: bool = False,
) -> User:
    cursor = conn.execute(
        """
        INSERT INTO users (name, password, is_active, is_admin, must_change_password)
        VALUES (?, ?, ?, ?, 0)
        """,
        (name, password, 1 if is_active else 0, 1 if is_admin else 0),
    )
    user_id = cursor.lastrowid
    assert user_id is not None
    return User(
        user_id=user_id,
        name=name,
        password=password,
        is_active=is_active,
        is_admin=is_admin,
    )


@pytest.fixture
def admin_user(db_session: sqlite3.Connection) -> User:
    return _insert_user(db_session, name="admin", password=hash_password("secret"), is_admin=True)


@pytest_asyncio.fixture
async def admin_token(client, admin_user):
    response = await client.post(
        "/api/v1/auth/login", json={"username": "admin", "password": "secret"}
    )
    return response.json()["access_token"]


@pytest.fixture
def regular_user(db_session: sqlite3.Connection) -> User:
    return _insert_user(
        db_session, name="regular", password=hash_password("secret"), is_admin=False
    )


@pytest_asyncio.fixture
async def regular_token(client, regular_user):
    response = await client.post(
        "/api/v1/auth/login", json={"username": "regular", "password": "secret"}
    )
    return response.json()["access_token"]


@pytest.fixture
def mock_connection() -> MagicMock:
    connection = MagicMock(spec=ConnectionBase)
    connection.connection_id = "mock_connection"
    connection.is_available = AsyncMock(return_value=True)
    connection.get_host_state = AsyncMock()
    connection.get_service_state = AsyncMock()
    connection.get_host_hard_state = AsyncMock()
    connection.get_service_hard_state = AsyncMock()
    connection.get_hostgroup_states = AsyncMock()
    connection.get_servicegroup_states = AsyncMock()
    connection.get_hosts_states = AsyncMock(return_value={})
    connection.get_services_states = AsyncMock(return_value={})
    connection.get_hosts_services_batch = AsyncMock(return_value={})
    connection.get_host_services = AsyncMock(return_value=[])
    connection.get_services_summary = AsyncMock(return_value={})
    connection.get_objects = AsyncMock(return_value=[])
    connection.get_group_members = AsyncMock(return_value=[])
    connection.get_topology = AsyncMock(return_value=[])
    return connection
