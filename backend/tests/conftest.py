"""Test fixtures and configuration."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.backends.base import BackendBase
from app.core.database import Base, get_db
from app.core.security import hash_password
from app.main import app
from app.models.user import User

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(TEST_DB_URL, echo=False)
TestSessionLocal = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    import app.models  # noqa: F401

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session():
    async with TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_session: AsyncSession):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession) -> User:
    user = User(
        name="admin",
        password=hash_password("secret"),
        is_active=True,
        is_admin=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def admin_token(client, admin_user):
    response = await client.post(
        "/api/v1/auth/login", json={"username": "admin", "password": "secret"}
    )
    return response.json()["access_token"]


@pytest_asyncio.fixture
async def regular_user(db_session: AsyncSession) -> User:
    user = User(
        name="regular",
        password=hash_password("secret"),
        is_active=True,
        is_admin=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def regular_token(client, regular_user):
    response = await client.post(
        "/api/v1/auth/login", json={"username": "regular", "password": "secret"}
    )
    return response.json()["access_token"]


@pytest.fixture
def mock_backend() -> MagicMock:
    """A MagicMock implementing BackendBase for unit tests."""
    backend = MagicMock(spec=BackendBase)
    backend.backend_id = "mock_backend"
    backend.is_available = AsyncMock(return_value=True)
    backend.get_host_state = AsyncMock()
    backend.get_service_state = AsyncMock()
    backend.get_host_hard_state = AsyncMock()
    backend.get_service_hard_state = AsyncMock()
    backend.get_hostgroup_states = AsyncMock()
    backend.get_servicegroup_states = AsyncMock()
    backend.get_hosts_states = AsyncMock(return_value={})
    backend.get_services_states = AsyncMock(return_value={})
    backend.get_hosts_services_batch = AsyncMock(return_value={})
    backend.get_host_services = AsyncMock(return_value=[])
    backend.get_objects = AsyncMock(return_value=[])
    backend.get_group_members = AsyncMock(return_value=[])
    backend.get_topology = AsyncMock(return_value=[])
    return backend
