"""Backend tests."""

import pytest

from app.backends.test import TestBackend


@pytest.mark.asyncio
async def test_test_backend_host_state():
    backend = TestBackend()
    state = await backend.get_host_state("localhost")
    assert state.type == "host"
    assert state.state in ("UP", "DOWN", "UNREACHABLE")


@pytest.mark.asyncio
async def test_test_backend_service_state():
    backend = TestBackend()
    state = await backend.get_service_state("localhost", "HTTP")
    assert state.type == "service"
    assert state.state in ("OK", "WARNING", "CRITICAL", "UNKNOWN")


@pytest.mark.asyncio
async def test_test_backend_get_objects():
    backend = TestBackend()
    hosts = await backend.get_objects("host")
    assert len(hosts) > 0
    assert "localhost" in hosts


@pytest.mark.asyncio
async def test_test_backend_is_available():
    backend = TestBackend()
    assert await backend.is_available() is True
