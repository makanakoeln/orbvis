"""Connection tests."""

import pytest

from app.connections.test import TestConnection


@pytest.mark.asyncio
async def test_test_backend_host_state():
    connection = TestConnection()
    state = await connection.get_host_state("localhost")
    assert state.type == "host"
    assert state.state in ("UP", "DOWN", "UNREACHABLE")


@pytest.mark.asyncio
async def test_test_connection_service_state():
    connection = TestConnection()
    state = await connection.get_service_state("localhost", "HTTP")
    assert state.type == "service"
    assert state.state in ("OK", "WARNING", "CRITICAL", "UNKNOWN")


@pytest.mark.asyncio
async def test_test_backend_get_objects():
    connection = TestConnection()
    hosts = await connection.get_objects("host")
    assert len(hosts) > 0
    assert "localhost" in hosts


@pytest.mark.asyncio
async def test_test_backend_is_available():
    connection = TestConnection()
    assert await connection.is_available() is True
