"""Connection tests."""

import asyncio

import pytest

from app.connections.livestatus import LivestatusConnection, _apply_extra
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


def _make_livestatus_connection() -> LivestatusConnection:
    """LivestatusConnection without opening a real socket. Tests stub `_query`."""
    return LivestatusConnection(socket_path="/dev/null")


@pytest.mark.asyncio
async def test_bulk_services_chunks_and_runs_in_parallel(monkeypatch):
    """25-host batch with chunk_size=5 must fan out to 5 concurrent queries.

    Uses an ``asyncio.Barrier`` to prove parallelism deterministically: every
    chunk query must reach the barrier before any returns, so the test fails
    fast on serial execution rather than relying on timing.
    """
    monkeypatch.setattr("app.core.config.settings.flow_board_bulk_service_chunk_size", 5)
    connection = _make_livestatus_connection()

    chunk_args: list[list[str]] = []
    barrier = asyncio.Barrier(5)

    async def _fake_query(query: str) -> list[list[object]]:
        hosts = [
            line.split("=", 1)[1].strip()
            for line in query.splitlines()
            if line.startswith("Filter: host_name =")
        ]
        chunk_args.append(hosts)
        await barrier.wait()
        return [[h, f"{h}/svc", 0, "ok"] for h in hosts]

    monkeypatch.setattr(connection, "_query", _fake_query)

    hostnames = [f"h{i:02d}" for i in range(25)]
    result = await connection.get_hosts_services_batch(hostnames)

    assert len(chunk_args) == 5
    assert sorted(c for chunk in chunk_args for c in chunk) == sorted(hostnames)
    assert sorted(result.keys()) == sorted(hostnames)
    for h, svcs in result.items():
        assert [s["name"] for s in svcs] == [f"{h}/svc"]


@pytest.mark.asyncio
async def test_bulk_services_empty_input_skips_query(monkeypatch):
    connection = _make_livestatus_connection()
    called = False

    async def _fake_query(_query: str) -> list[list[object]]:
        nonlocal called
        called = True
        return []

    monkeypatch.setattr(connection, "_query", _fake_query)
    assert await connection.get_hosts_services_batch([]) == {}
    assert called is False


@pytest.mark.asyncio
async def test_bulk_services_smaller_than_chunk_size_runs_one_query(monkeypatch):
    """Three hosts with chunk_size=5 must collapse into a single query."""
    monkeypatch.setattr("app.core.config.settings.flow_board_bulk_service_chunk_size", 5)
    connection = _make_livestatus_connection()
    calls = 0

    async def _fake_query(_query: str) -> list[list[object]]:
        nonlocal calls
        calls += 1
        return [["h1", "svc-a", 0, ""]]

    monkeypatch.setattr(connection, "_query", _fake_query)
    result = await connection.get_hosts_services_batch(["h1", "h2", "h3"])
    assert calls == 1
    assert result["h1"][0]["name"] == "svc-a"
    assert result["h2"] == [] and result["h3"] == []
