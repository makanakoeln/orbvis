"""Connection tests."""

import pytest

from app.connections.livestatus import _apply_extra
from app.connections.test import TestConnection
from app.schemas.state import ObjectState


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


@pytest.mark.asyncio
async def test_test_backend_services_summary():
    connection = TestConnection()
    summary = await connection.get_services_summary(["localhost"])
    assert "localhost" in summary
    counts = summary["localhost"]
    # Total must equal the number of demo services for the host.
    assert counts.ok + counts.warning + counts.critical + counts.unknown + counts.pending == 10


@pytest.mark.asyncio
async def test_test_backend_host_state_carries_alias_and_timing():
    connection = TestConnection()
    state = await connection.get_host_state("localhost")
    assert state.alias == "alias-localhost"
    assert state.last_check is not None
    assert state.next_check is not None
    assert state.next_check > state.last_check
    assert state.state_type == "HARD"
    assert state.max_attempts == 3


def test_apply_extra_host_columns_map_correctly():
    """Verify _apply_extra reads the correct column offsets after schema changes.

    Layout (host, after standard 5-col prefix at offset=5):
      [5]=address [6]=alias [7]=last_check [8]=next_check [9]=state_type
      [10]=current_attempt [11]=max_check_attempts [12]=last_state_change
      [13]=notifications_enabled [14]=active_checks_enabled
    """
    state = ObjectState(object_id="", type="host", state="UP")
    row = [
        0,
        "out",
        "",
        0,
        0,
        "192.0.2.1",  # address
        "ALIAS",  # alias
        1700.0,  # last_check
        1760.0,  # next_check
        1,  # state_type=HARD
        2,  # current_attempt
        3,  # max_attempts
        1500.0,  # last_state_change
        1,  # notifications_enabled
        0,  # active_checks_enabled
    ]
    _apply_extra(state, row, offset=5, include_address=True)
    assert state.address == "192.0.2.1"
    assert state.alias == "ALIAS"
    assert state.last_check == 1700.0
    assert state.next_check == 1760.0
    assert state.state_type == "HARD"
    assert state.current_attempt == 2
    assert state.max_attempts == 3
    assert state.last_state_change == 1500.0
    assert state.notifications_enabled is True
    assert state.active_checks_enabled is False


def test_apply_extra_service_columns_map_correctly():
    """Service rows have no alias slot — only next_check is added."""
    state = ObjectState(object_id="", type="service", state="OK")
    row = [
        "h",
        "s",
        0,
        "out",
        "",
        0,
        0,
        1700.0,  # last_check
        1760.0,  # next_check
        0,  # state_type=SOFT
        2,  # current_attempt
        3,  # max_attempts
        1500.0,  # last_state_change
        1,  # notifications_enabled
        1,  # active_checks_enabled
    ]
    _apply_extra(state, row, offset=7)
    assert state.last_check == 1700.0
    assert state.next_check == 1760.0
    assert state.state_type == "SOFT"
    assert state.current_attempt == 2
    assert state.max_attempts == 3
    assert state.last_state_change == 1500.0
