"""Tests for state aggregation logic in state_service."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.schemas.board import BoardConfig, BoardObject, StaticView
from app.schemas.state import ObjectState
from app.services import state_service
from app.services.state_service import (
    _aggregate_host_with_services_from_data,
    get_board_states,
    get_connection,
    get_connection_objects,
    register_connection,
)


def _host_state(object_id: str, state: str) -> ObjectState:
    return ObjectState(object_id=object_id, type="host", state=state)


def _svc_state(object_id: str, state: str) -> ObjectState:
    return ObjectState(object_id=object_id, type="service", state=state)


def _board(objects: list[BoardObject], connection_id: str = "mock") -> BoardConfig:
    return BoardConfig(
        name="test", alias="Test", connection_id=connection_id, view=StaticView(), objects=objects
    )


def _obj(id: str, type: str = "host", **kwargs) -> BoardObject:
    return BoardObject(id=id, type=type, **kwargs)


# ---------------------------------------------------------------------------
# register_connection / get_connection
# ---------------------------------------------------------------------------


def test_register_and_get_backend(mock_connection, monkeypatch):
    monkeypatch.setattr(state_service, "_connections", {})
    register_connection("mybackend", mock_connection)
    assert get_connection("mybackend") is mock_connection


def test_get_backend_not_found(monkeypatch):
    monkeypatch.setattr(state_service, "_connections", {})
    assert get_connection("nonexistent") is None


# ---------------------------------------------------------------------------
# get_connection_objects
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_backend_objects_no_backend(monkeypatch):
    monkeypatch.setattr(state_service, "_connections", {})
    result = await get_connection_objects("missing", "host")
    assert result == []


@pytest.mark.asyncio
async def test_get_backend_objects_returns_list(mock_connection, monkeypatch):
    monkeypatch.setattr(state_service, "_connections", {"mock": mock_connection})
    mock_connection.get_objects = AsyncMock(return_value=["host1", "host2"])
    result = await get_connection_objects("mock", "host")
    assert result == ["host1", "host2"]


@pytest.mark.asyncio
async def test_get_backend_objects_service_filter(mock_connection, monkeypatch):
    monkeypatch.setattr(state_service, "_connections", {"mock": mock_connection})
    mock_connection.get_objects = AsyncMock(return_value=["srv1;CPU", "srv1;RAM", "srv2;CPU"])
    result = await get_connection_objects("mock", "service", host="srv1")
    assert result == ["CPU", "RAM"]


# ---------------------------------------------------------------------------
# _aggregate_host_with_services_from_data — pure logic
# ---------------------------------------------------------------------------


def test_aggregate_no_services_returns_host_state():
    host = _host_state("h1", "UP")
    result = _aggregate_host_with_services_from_data(host, [])
    assert result.state == "UP"
    assert result is host  # same object returned


def test_aggregate_service_warning_wins_over_up():
    host = _host_state("h1", "UP")
    services = [{"state": "WARNING"}, {"state": "OK"}]
    result = _aggregate_host_with_services_from_data(host, services)
    assert result.state == "WARNING"


def test_aggregate_host_down_wins_over_warning():
    host = _host_state("h1", "DOWN")
    services = [{"state": "WARNING"}]
    result = _aggregate_host_with_services_from_data(host, services)
    assert result.state == "DOWN"


def test_aggregate_critical_wins_over_down():
    host = _host_state("h1", "DOWN")
    services = [{"state": "CRITICAL"}]
    result = _aggregate_host_with_services_from_data(host, services)
    assert result.state == "CRITICAL"


def test_aggregate_all_ok_returns_host_state():
    host = _host_state("h1", "UP")
    services = [{"state": "OK"}, {"state": "OK"}]
    result = _aggregate_host_with_services_from_data(host, services)
    assert result.state == "UP"


def test_aggregate_preserves_metadata():
    host = ObjectState(
        object_id="h1",
        type="host",
        state="UP",
        output="PING OK",
        acknowledged=True,
        in_downtime=True,
    )
    services = [{"state": "WARNING"}]
    result = _aggregate_host_with_services_from_data(host, services)
    assert result.state == "WARNING"
    assert result.output == "PING OK"
    assert result.acknowledged is True
    assert result.in_downtime is True


# ---------------------------------------------------------------------------
# get_board_states — no connection registered
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_board_states_no_backend(monkeypatch):
    monkeypatch.setattr(state_service, "_connections", {})
    board = _board(
        [
            _obj("h1", "host", host_name="srv1"),
            _obj("s1", "service", host_name="srv1", service_description="CPU"),
        ],
        connection_id="missing",
    )
    result = await get_board_states(board)
    assert result.connection_ok is False
    assert all(s.state == "PENDING" for s in result.states)
    assert len(result.states) == 2


# ---------------------------------------------------------------------------
# get_board_states — with mock connection
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_board_states_with_backend(mock_connection, monkeypatch):
    monkeypatch.setattr(state_service, "_connections", {"mock": mock_connection})

    host_state = ObjectState(object_id="h1", type="host", state="UP")
    mock_connection.get_hosts_states = AsyncMock(return_value={"srv1": host_state})

    board = _board([_obj("h1", "host", host_name="srv1")], connection_id="mock")
    result = await get_board_states(board)

    assert result.connection_ok is True
    assert result.states[0].state == "UP"
    assert result.states[0].object_id == "h1"


@pytest.mark.asyncio
async def test_get_board_states_batch_exception_yields_pending(mock_connection, monkeypatch):
    monkeypatch.setattr(state_service, "_connections", {"mock": mock_connection})

    mock_connection.get_hosts_states = AsyncMock(side_effect=Exception("socket error"))

    board = _board([_obj("h1", "host", host_name="srv1")], connection_id="mock")
    result = await get_board_states(board)

    # All monitoring states stale → connection_ok=False
    assert result.connection_ok is False
    assert result.states[0].state == "PENDING"
    assert result.states[0].stale is True


@pytest.mark.asyncio
async def test_get_board_states_non_monitoring_objects(mock_connection, monkeypatch):
    monkeypatch.setattr(state_service, "_connections", {"mock": mock_connection})
    mock_connection.is_available = AsyncMock(return_value=True)

    # textbox and image are non-monitoring types → connection_ok determined by is_available
    board = _board(
        [_obj("t1", "textbox"), _obj("i1", "image")],
        connection_id="mock",
    )
    result = await get_board_states(board)
    assert result.connection_ok is True
    # Both non-monitoring objects get PENDING state
    assert all(s.state == "PENDING" for s in result.states)
