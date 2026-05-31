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
    mock_connection.get_objects = AsyncMock(return_value=["srv1;CPU", "srv1;RAM"])
    result = await get_connection_objects("mock", "service", host="srv1")
    assert result == ["CPU", "RAM"]
    # host must reach the backend, else large environments time out
    mock_connection.get_objects.assert_awaited_once_with("service", "srv1", None)


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
async def test_map_link_aggregates_nested_map_states(mock_connection, monkeypatch):
    """A Map-A → Map-B → host(CRIT) chain must surface CRIT on the top-level link.

    Before this aggregation supported recursion, intermediate map links were
    filtered out and the parent link aggregated to PENDING.
    """
    from app.services import board_service

    monkeypatch.setattr(state_service, "_connections", {"mock": mock_connection})

    # Two stored boards: ``inner`` holds a CRIT host, ``outer`` only references inner.
    inner = _board(
        [_obj("h_inner", "host", host_name="srv-crit")],
        connection_id="mock",
    )
    inner.name = "inner"
    leaf = _board(
        [_obj("link_to_inner", "map", map_name="inner")],
        connection_id="mock",
    )
    leaf.name = "leaf"
    outer = _board(
        [_obj("link_to_leaf", "map", map_name="leaf")],
        connection_id="mock",
    )
    outer.name = "outer"

    boards = {"inner": inner, "leaf": leaf, "outer": outer}
    monkeypatch.setattr(board_service, "get_board", boards.get)
    mock_connection.get_hosts_states = AsyncMock(
        return_value={"srv-crit": ObjectState(object_id="h_inner", type="host", state="DOWN")}
    )

    result = await get_board_states(outer)
    by_id = {s.object_id: s for s in result.states}
    assert by_id["link_to_leaf"].state == "DOWN"


@pytest.mark.asyncio
async def test_map_link_handles_cycle_without_recursion(mock_connection, monkeypatch):
    """Self-referential map cycle must not stack-overflow; result is PENDING."""
    from app.services import board_service

    monkeypatch.setattr(state_service, "_connections", {"mock": mock_connection})

    # Board A links to B, B links back to A — pure cycle, no leaves.
    a = _board([_obj("a_to_b", "map", map_name="b")], connection_id="mock")
    a.name = "a"
    b = _board([_obj("b_to_a", "map", map_name="a")], connection_id="mock")
    b.name = "b"
    monkeypatch.setattr(board_service, "get_board", {"a": a, "b": b}.get)
    mock_connection.is_available = AsyncMock(return_value=True)

    result = await get_board_states(a)
    by_id = {s.object_id: s for s in result.states}
    assert by_id["a_to_b"].state == "PENDING"


@pytest.mark.asyncio
async def test_per_object_connection_override_routes_to_other_backend(mock_connection, monkeypatch):
    """An object's ``connection_id`` overrides the board default."""
    primary = mock_connection
    secondary = AsyncMock()
    secondary.get_hosts_states = AsyncMock(
        return_value={
            "remote-host": ObjectState(object_id="remote-host", type="host", state="DOWN")
        }
    )
    secondary.is_available = AsyncMock(return_value=True)

    primary.get_hosts_states = AsyncMock(
        return_value={"local-host": ObjectState(object_id="local-host", type="host", state="UP")}
    )

    monkeypatch.setattr(state_service, "_connections", {"primary": primary, "secondary": secondary})

    board = _board(
        [
            _obj("local", "host", host_name="local-host"),
            _obj("remote", "host", host_name="remote-host", connection_id="secondary"),
        ],
        connection_id="primary",
    )
    result = await get_board_states(board)
    by_id = {s.object_id: s for s in result.states}
    assert by_id["local"].state == "UP"
    assert by_id["remote"].state == "DOWN"
    primary.get_hosts_states.assert_called_once()
    secondary.get_hosts_states.assert_called_once()


@pytest.mark.asyncio
async def test_worldmap_auto_source_inflates_geo_hosts(mock_connection, monkeypatch):
    """worldmap.auto_source pulls hosts with geo coords into transient objects."""
    from app.schemas.board import WorldmapView

    mock_connection.get_hosts_states = AsyncMock(
        return_value={
            "ham-srv1": ObjectState(object_id="ham-srv1", type="host", state="UP"),
            "muc-srv1": ObjectState(object_id="muc-srv1", type="host", state="DOWN"),
        }
    )
    mock_connection.get_hosts_with_geo = AsyncMock(
        return_value=[
            {"name": "ham-srv1", "alias": "Hamburg srv1", "lat": 53.5, "lng": 10.0},
            {"name": "muc-srv1", "alias": "Munich srv1", "lat": 48.1, "lng": 11.5},
        ]
    )
    monkeypatch.setattr(state_service, "_connections", {"mock": mock_connection})

    cfg = BoardConfig(
        name="geo",
        alias="Geo",
        connection_id="mock",
        view=WorldmapView(auto_source="all_hosts"),
        objects=[],
    )
    result = await get_board_states(cfg)
    by_id = {s.object_id: s for s in result.states}
    assert by_id["auto:ham-srv1"].state == "UP"
    assert by_id["auto:muc-srv1"].state == "DOWN"


@pytest.mark.asyncio
async def test_worldmap_auto_source_skips_persisted_duplicates(mock_connection, monkeypatch):
    """Persisted objects with matching host names win over auto-discovered duplicates."""
    from app.schemas.board import WorldmapView

    mock_connection.get_hosts_states = AsyncMock(
        return_value={"srv1": ObjectState(object_id="srv1", type="host", state="DOWN")}
    )
    mock_connection.get_hosts_with_geo = AsyncMock(
        return_value=[{"name": "srv1", "alias": "srv1", "lat": 1.0, "lng": 2.0}]
    )
    monkeypatch.setattr(state_service, "_connections", {"mock": mock_connection})

    cfg = BoardConfig(
        name="geo",
        alias="Geo",
        connection_id="mock",
        view=WorldmapView(auto_source="all_hosts"),
        objects=[BoardObject(id="manual_srv1", type="host", host_name="srv1", lat=10, lng=20)],
    )
    result = await get_board_states(cfg)
    ids = {s.object_id for s in result.states}
    assert "manual_srv1" in ids
    assert "auto:srv1" not in ids


@pytest.mark.asyncio
async def test_per_object_connection_override_unregistered_yields_pending(
    mock_connection, monkeypatch
):
    monkeypatch.setattr(state_service, "_connections", {"primary": mock_connection})
    mock_connection.get_hosts_states = AsyncMock(return_value={})

    board = _board(
        [_obj("orphan", "host", host_name="anywhere", connection_id="ghost")],
        connection_id="primary",
    )
    result = await get_board_states(board)
    by_id = {s.object_id: s for s in result.states}
    assert by_id["orphan"].state == "PENDING"
    assert by_id["orphan"].stale is True


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


# ---------------------------------------------------------------------------
# Topology snapshot diff (used by the Flow Board WebSocket broadcast loop)
# ---------------------------------------------------------------------------


def _topo_node(name: str, **kwargs):
    """Build a TopologyNode with sensible defaults for diff tests."""
    from app.api.v1.connections import TopologyNode

    return TopologyNode(**{"parents": [], "state": "UP", "output": "ok", "name": name, **kwargs})


@pytest.fixture(autouse=True)
def _clear_topology_snapshots():
    state_service._topology_snapshots.clear()
    yield
    state_service._topology_snapshots.clear()


def test_topology_delta_first_call_is_full():
    nodes = [_topo_node("h1"), _topo_node("h2")]
    delta = state_service.compute_topology_delta("b1", None, nodes)
    assert delta.full is True
    assert {n.name for n in delta.added} == {"h1", "h2"}
    assert delta.changed == [] and delta.removed == []


def test_topology_delta_no_changes_returns_empty_lists():
    nodes = [_topo_node("h1"), _topo_node("h2")]
    state_service.compute_topology_delta("b1", None, nodes)
    delta = state_service.compute_topology_delta("b1", None, nodes)
    assert delta.full is False
    assert delta.added == [] and delta.changed == [] and delta.removed == []


def test_topology_delta_detects_added_host():
    state_service.compute_topology_delta("b1", None, [_topo_node("h1")])
    delta = state_service.compute_topology_delta("b1", None, [_topo_node("h1"), _topo_node("h2")])
    assert [n.name for n in delta.added] == ["h2"]
    assert delta.changed == [] and delta.removed == []


def test_topology_delta_detects_changed_volatile_field():
    state_service.compute_topology_delta("b1", None, [_topo_node("h1", state="UP", output="ok")])
    delta = state_service.compute_topology_delta(
        "b1", None, [_topo_node("h1", state="DOWN", output="boom")]
    )
    assert [n.name for n in delta.changed] == ["h1"]
    assert delta.added == [] and delta.removed == []


def test_topology_delta_detects_removed_host():
    state_service.compute_topology_delta("b1", None, [_topo_node("h1"), _topo_node("h2")])
    delta = state_service.compute_topology_delta("b1", None, [_topo_node("h1")])
    assert delta.removed == ["h2"]
    assert delta.added == [] and delta.changed == []


def test_topology_delta_ignores_stable_field_change():
    # alias is metadata, not a volatile field — changing it should NOT trigger a delta.
    state_service.compute_topology_delta("b1", None, [_topo_node("h1", alias="old")])
    delta = state_service.compute_topology_delta("b1", None, [_topo_node("h1", alias="new")])
    assert delta.added == [] and delta.changed == [] and delta.removed == []


def test_topology_delta_force_full_resends_everything():
    nodes = [_topo_node("h1"), _topo_node("h2")]
    state_service.compute_topology_delta("b1", None, nodes)
    delta = state_service.compute_topology_delta("b1", None, nodes, force_full=True)
    assert delta.full is True
    assert {n.name for n in delta.added} == {"h1", "h2"}


def test_topology_delta_per_user_isolation():
    # Different auth_users see different host sets — snapshots must not collide.
    state_service.compute_topology_delta("b1", "alice", [_topo_node("h1")])
    state_service.compute_topology_delta("b1", "bob", [_topo_node("h2")])
    # Bob's second call: nothing changed, expect empty diff.
    delta_bob = state_service.compute_topology_delta("b1", "bob", [_topo_node("h2")])
    assert delta_bob.full is False
    assert delta_bob.added == [] and delta_bob.changed == [] and delta_bob.removed == []


def test_drop_topology_snapshot_clears_all_users_for_board():
    state_service.compute_topology_delta("b1", "alice", [_topo_node("h1")])
    state_service.compute_topology_delta("b1", "bob", [_topo_node("h2")])
    state_service.compute_topology_delta("b2", None, [_topo_node("h3")])
    state_service.drop_topology_snapshot("b1")
    assert all(k[0] != "b1" for k in state_service._topology_snapshots)
    assert ("b2", None) in state_service._topology_snapshots


@pytest.mark.asyncio
async def test_fetch_topology_passes_flow_view_filter(mock_connection, monkeypatch):
    """Per-board root/child_layers/parent_layers must reach build_topology_response.

    Regression for the bug where the WS push path ignored these fields,
    silently overriding the filtered REST response with a full topology.
    """
    from app.api.v1 import states as states_api
    from app.schemas.board import FlowView

    monkeypatch.setattr(state_service, "_connections", {"live_1": mock_connection})

    captured: dict[str, object] = {}

    async def fake_build(connection, **kwargs):
        captured.update(kwargs)
        return []

    monkeypatch.setattr(states_api, "build_topology_response", fake_build)

    cfg = BoardConfig(
        name="flow1",
        alias="Flow 1",
        connection_id="live_1",
        view=FlowView(root="core-router-01", child_layers=2, parent_layers=1),
    )
    await states_api._fetch_topology_for_user(cfg, auth_user=None)

    assert captured["root"] == "core-router-01"
    assert captured["child_layers"] == 2
    assert captured["parent_layers"] == 1


# --- compute_states_delta: slim timing patches ------------------------------


def _timed(object_id: str, state: str, *, last: float, nxt: float, attempt: int = 1) -> ObjectState:
    return ObjectState(
        object_id=object_id,
        type="host",
        state=state,
        last_check=last,
        next_check=nxt,
        current_attempt=attempt,
    )


def test_timing_delta_first_call_is_full_without_timing() -> None:
    board = "timing-board-1"
    state_service.drop_states_snapshot(board)
    cur = [_timed("h1", "UP", last=10, nxt=70)]

    to_send, removed, full, timing = state_service.compute_states_delta(board, None, cur)

    assert full is True
    assert to_send == cur
    assert removed == []
    assert timing == []  # full send already carries timing inside the state


def test_timing_only_change_rides_slim_patch_not_full_state() -> None:
    board = "timing-board-2"
    state_service.drop_states_snapshot(board)
    state_service.compute_states_delta(board, None, [_timed("h1", "UP", last=10, nxt=70)])

    # Same operational state, only the check times moved forward (SmartPing).
    to_send, removed, full, timing = state_service.compute_states_delta(
        board, None, [_timed("h1", "UP", last=70, nxt=130)]
    )

    assert full is False
    assert removed == []
    assert to_send == []  # no full re-send
    assert [t.object_id for t in timing] == ["h1"]
    assert timing[0].next_check == 130
    assert timing[0].last_check == 70


def test_operational_change_carries_timing_inline_not_duplicated() -> None:
    board = "timing-board-3"
    state_service.drop_states_snapshot(board)
    state_service.compute_states_delta(board, None, [_timed("h1", "UP", last=10, nxt=70)])

    # State flipped *and* timing moved: object is in to_send, so it must not
    # also appear in the slim timing list.
    to_send, removed, full, timing = state_service.compute_states_delta(
        board, None, [_timed("h1", "DOWN", last=70, nxt=130)]
    )

    assert [s.object_id for s in to_send] == ["h1"]
    assert full is False
    assert removed == []
    assert timing == []


def test_no_change_sends_nothing() -> None:
    board = "timing-board-4"
    state_service.drop_states_snapshot(board)
    same = [_timed("h1", "UP", last=10, nxt=70)]
    state_service.compute_states_delta(board, None, same)

    to_send, removed, full, timing = state_service.compute_states_delta(
        board, None, [_timed("h1", "UP", last=10, nxt=70)]
    )

    assert full is False
    assert to_send == []
    assert removed == []
    assert timing == []


# ---------------------------------------------------------------------------
# Folder-tree board (concept v3)
# ---------------------------------------------------------------------------


def _folder_board(view_kwargs: dict | None = None) -> BoardConfig:
    from app.schemas.board import FolderTreeView

    return BoardConfig(
        name="ft",
        alias="FT",
        connection_id="test",
        view=FolderTreeView(**(view_kwargs or {})),
        objects=[],
    )


def _find_node(node, path):
    if node.path == path:
        return node
    for child in node.children:
        found = _find_node(child, path)
        if found is not None:
            return found
    return None


@pytest.fixture
def _test_conn(monkeypatch):
    from app.connections.test import TestConnection

    conn = TestConnection()
    monkeypatch.setattr(state_service, "_connections", {"test": conn})
    return conn


@pytest.mark.asyncio
async def test_foldertree_builds_tree_with_empty_folders(_test_conn):
    result = await get_board_states(_folder_board())
    tree = result.folder_tree
    assert tree is not None and tree.path == ""
    # Nested + empty folders present.
    muc = _find_node(tree, "datacenters/muc")
    assert muc is not None and muc.kind == "folder" and muc.host_count == 2
    staging = _find_node(tree, "staging")
    assert staging is not None and staging.is_empty and staging.state == "EMPTY"
    # Container folder "datacenters" is not empty (has populated subfolders).
    dc = _find_node(tree, "datacenters")
    assert dc is not None and not dc.is_empty
    # Empty folder is excluded from the root's worst-state.
    assert tree.state != "EMPTY"


@pytest.mark.asyncio
async def test_foldertree_severity_counts_bubble_by_host_state(_test_conn):
    result = await get_board_states(_folder_board())
    tree = result.folder_tree
    # Per-folder host severity breakdown, problem states only; sums to problem_count.
    for node in (tree, _find_node(tree, "datacenters"), _find_node(tree, "datacenters/muc")):
        assert sum(node.severity_counts.values()) == node.problem_count
        assert all(state_service._COMBINED_SEVERITY.get(s, 0) > 0 for s in node.severity_counts)
    # OK/UP hosts are not counted; service leaves never feed the breakdown.
    muc = _find_node(tree, "datacenters/muc")
    assert "OK" not in muc.severity_counts and "UP" not in muc.severity_counts


@pytest.mark.asyncio
async def test_foldertree_hide_empty_folders(_test_conn):
    result = await get_board_states(_folder_board({"show_empty_folders": False}))
    assert _find_node(result.folder_tree, "staging") is None
    assert _find_node(result.folder_tree, "decommissioned") is None
    # Populated folders remain.
    assert _find_node(result.folder_tree, "datacenters/muc") is not None


@pytest.mark.asyncio
async def test_foldertree_prunes_unpermitted_empty_folders(_test_conn, monkeypatch):
    """A scoped user must not see SETUP folder names they have no access to.

    Empty folders the user can't read (``permitted=False``) are pruned even with
    ``show_empty_folders`` on; an empty *permitted* folder is kept, and a folder
    that contains a visible host is kept regardless of its own permission flag.
    """
    from app.connections.base import FolderTreeData

    async def _fake_folder_tree(*, only_hard=False, sites=None):
        return FolderTreeData(
            folders=[
                {"path": "", "title": "Main", "permitted": True},
                {"path": "secret", "title": "Secret", "permitted": False},
                {"path": "shared", "title": "Shared", "permitted": True},
                {"path": "withhost", "title": "WithHost", "permitted": False},
            ],
            hosts=[
                {
                    "host_name": "h1",
                    "folder_path": "withhost",
                    "state": "UP",
                    "output": "",
                    "site_id": "central",
                }
            ],
        )

    monkeypatch.setattr(_test_conn, "get_folder_tree", _fake_folder_tree)
    result = await get_board_states(_folder_board({"show_empty_folders": True}))
    tree = result.folder_tree
    # Empty + not permitted → hidden, even though show_empty_folders is on.
    assert _find_node(tree, "secret") is None
    # Empty + permitted → shown (respects show_empty_folders).
    assert _find_node(tree, "shared") is not None
    # Has a visible host → shown regardless of its own permission flag.
    wh = _find_node(tree, "withhost")
    assert wh is not None and wh.host_count == 1


@pytest.mark.asyncio
async def test_foldertree_sites_filter(_test_conn):
    result = await get_board_states(_folder_board({"sites": ["central"]}))
    tree = result.folder_tree
    # Frankfurt only had a remote_fra host → no longer populated.
    fra = _find_node(tree, "datacenters/fra")
    assert fra is None or fra.is_empty
    # central hosts still placed.
    assert _find_node(tree, "datacenters/muc").host_count == 2
    assert all(s.site_id == "central" for s in result.states)


@pytest.mark.asyncio
async def test_foldertree_root_scoping(_test_conn):
    result = await get_board_states(_folder_board({"root_folder": "network"}))
    tree = result.folder_tree
    assert tree.path == "network"
    # Subtree only — datacenters not reachable from this root.
    assert _find_node(tree, "datacenters") is None


@pytest.mark.asyncio
async def test_foldertree_show_services_is_not_eager(_test_conn):
    # show_services must NOT materialise service leaves into the SSE tree — that
    # would issue a global all-services query (ignores folder scope) and break on
    # 4M-host sites. Services are fetched lazily per host via the endpoint instead.
    result = await get_board_states(_folder_board({"show_services": True}))
    host = _find_node(result.folder_tree, "datacenters/muc/localhost")
    assert host is not None and host.kind == "host"
    assert not host.children, "show_services must not eagerly attach service leaves"


@pytest.mark.asyncio
async def test_foldertree_no_services_by_default(_test_conn):
    result = await get_board_states(_folder_board())
    host = _find_node(result.folder_tree, "datacenters/muc/localhost")
    assert host is not None and not host.children


def test_folder_tree_changed_signature():
    from app.schemas.state import FolderTreeNode

    def _tree(state="OK", output="rta 0.1ms"):
        return FolderTreeNode(
            path="dc",
            title="DC",
            kind="folder",
            state=state,
            children=[
                FolderTreeNode(path="dc/h1", title="h1", kind="host", state=state, output=output)
            ],
        )

    key = ("ftsig", None)
    state_service._folder_tree_sigs.pop(key, None)
    assert state_service.folder_tree_changed("ftsig", None, _tree()) is True
    # Same structure → no resend.
    assert state_service.folder_tree_changed("ftsig", None, _tree()) is False
    # Output drift alone must NOT force a resend.
    assert state_service.folder_tree_changed("ftsig", None, _tree(output="rta 9.9ms")) is False
    # A real state change does.
    assert state_service.folder_tree_changed("ftsig", None, _tree(state="CRITICAL")) is True
    state_service._folder_tree_sigs.pop(key, None)


@pytest.mark.asyncio
async def test_folder_host_services_endpoint_sorts_by_severity(client, admin_token, monkeypatch):
    from app.connections.base import ServiceRow
    from app.services import board_service

    board = _folder_board({"show_services": True})
    monkeypatch.setattr(board_service, "get_board", lambda name: board if name == "ft" else None)

    conn = AsyncMock()
    conn.get_host_services = AsyncMock(
        return_value=[
            ServiceRow(name="CPU", state="OK", output="all good"),
            ServiceRow(name="Disk", state="CRITICAL", output="full", acknowledged=True),
            ServiceRow(name="Mem", state="WARNING", output="high"),
        ]
    )
    monkeypatch.setattr(state_service, "get_connection", lambda cid: conn)

    resp = await client.get(
        "/api/v1/boards/ft/folder-host-services?host=h1",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    # Worst-state first (CRITICAL, WARNING, OK) — endpoint sorts independent of input order.
    assert [s["name"] for s in data] == ["Disk", "Mem", "CPU"]
    assert data[0]["acknowledged"] is True
    conn.get_host_services.assert_awaited_once_with("h1", only_hard=False)


@pytest.mark.asyncio
async def test_folder_host_services_endpoint_rejects_non_foldertree(
    client, admin_token, monkeypatch
):
    from app.services import board_service

    board = BoardConfig(name="st", alias="ST", connection_id="test", view=StaticView(), objects=[])
    monkeypatch.setattr(board_service, "get_board", lambda name: board if name == "st" else None)

    resp = await client.get(
        "/api/v1/boards/st/folder-host-services?host=h1",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_list_connection_folders(_test_conn):
    folders = await state_service.list_connection_folders("test")
    paths = [f["path"] for f in folders]
    titles = {f["path"]: f["title"] for f in folders}
    assert "" not in paths  # root excluded from the picker
    assert "datacenters" in paths and "datacenters/muc" in paths
    assert "staging" in paths  # empty folder still offered as a root choice
    assert titles["datacenters/muc"] == "Munich"  # real title preserved
    assert titles["network"] == "Network"  # prettified from slug
