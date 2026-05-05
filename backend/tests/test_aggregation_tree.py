"""Tests for BI aggregation tree fetching and standalone-mode hierarchy parsing."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.connections.livestatus import _hierarchy_to_node
from app.schemas.board import AggregationNode, BoardConfig, BoardObject, StaticView
from app.services import state_service


def _board_with_aggregation(expand_depth: int = 0) -> BoardConfig:
    return BoardConfig(
        name="t",
        alias="T",
        connection_id="mock",
        view=StaticView(),
        objects=[
            BoardObject(
                id="a1",
                type="aggregation",
                aggregation_id="Host localhost",
                expand_depth=expand_depth,
            )
        ],
    )


def _ajax_node(
    name: str,
    *,
    state: int = 0,
    node_type: str = "bi_aggregator",
    hostname: str = "",
    service: str = "",
    children: list[dict] | None = None,
) -> dict:
    """Build the dict shape that ajax_fetch_aggregation_data emits."""
    core: dict[str, object] = {"state": state, "in_downtime": False, "acknowledged": False}
    if hostname:
        core["hostname"] = hostname
    if service:
        core["service"] = service
    return {
        "name": name,
        "node_type": node_type,
        "type_specific": {"core": core},
        "children": children or [],
    }


# ---------------------------------------------------------------------------
# _hierarchy_to_node — standalone (REST/ajax) parsing + depth truncation
# ---------------------------------------------------------------------------


def test_hierarchy_parses_root_only_at_depth_zero():
    raw = _ajax_node(
        "Host localhost",
        children=[_ajax_node("Performance", children=[_ajax_node("CPU load", state=1)])],
    )
    node = _hierarchy_to_node(raw, depth=0, max_depth=0)
    assert node.name == "Host localhost"
    assert node.children == []  # truncated


def test_hierarchy_parses_one_level():
    raw = _ajax_node(
        "Host localhost",
        children=[
            _ajax_node(
                "Performance",
                state=1,
                children=[_ajax_node("CPU load", state=2, node_type="bi_leaf")],
            )
        ],
    )
    node = _hierarchy_to_node(raw, depth=0, max_depth=1)
    assert len(node.children) == 1
    assert node.children[0].name == "Performance"
    assert node.children[0].state == 1
    assert node.children[0].children == []  # truncated at depth 1


def test_hierarchy_extracts_leaf_host_and_service():
    raw = _ajax_node(
        "Aggregator",
        children=[
            _ajax_node(
                "CPU load", node_type="bi_leaf", hostname="srv01", service="CPU load", state=2
            )
        ],
    )
    node = _hierarchy_to_node(raw, depth=0, max_depth=2)
    leaf = node.children[0]
    assert leaf.node_type == "bi_leaf"
    assert leaf.host_name == "srv01"
    assert leaf.service_description == "CPU load"
    assert leaf.state == 2


# ---------------------------------------------------------------------------
# state_service: tree fetch + dedupe + ObjectState.tree wiring
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_state_service_attaches_tree_when_expand_depth_set(mock_connection, monkeypatch):
    cfg = _board_with_aggregation(expand_depth=2)
    tree = AggregationNode(name="Host localhost", node_type="bi_aggregator", state=0, children=[])

    mock_connection.get_aggregations_states = AsyncMock(return_value={})
    mock_connection.get_aggregation_tree = AsyncMock(return_value=tree)
    monkeypatch.setattr(state_service, "_connections", {"mock": mock_connection})

    result = await state_service.get_board_states(cfg, auth_user=None)
    assert len(result.states) == 1
    assert result.states[0].tree is not None
    assert result.states[0].tree.name == "Host localhost"
    mock_connection.get_aggregation_tree.assert_awaited_once_with("Host localhost", 2)


@pytest.mark.asyncio
async def test_state_service_skips_tree_when_expand_depth_zero(mock_connection, monkeypatch):
    cfg = _board_with_aggregation(expand_depth=0)
    mock_connection.get_aggregations_states = AsyncMock(return_value={})
    mock_connection.get_aggregation_tree = AsyncMock()
    monkeypatch.setattr(state_service, "_connections", {"mock": mock_connection})

    result = await state_service.get_board_states(cfg, auth_user=None)
    assert result.states[0].tree is None
    mock_connection.get_aggregation_tree.assert_not_awaited()


@pytest.mark.asyncio
async def test_state_service_dedupes_tree_fetches(mock_connection, monkeypatch):
    cfg = BoardConfig(
        name="t",
        alias="T",
        connection_id="mock",
        view=StaticView(),
        objects=[
            BoardObject(id="a1", type="aggregation", aggregation_id="A", expand_depth=2),
            BoardObject(id="a2", type="aggregation", aggregation_id="A", expand_depth=2),
            BoardObject(id="a3", type="aggregation", aggregation_id="B", expand_depth=2),
        ],
    )
    tree_a = AggregationNode(name="A", node_type="bi_aggregator", state=0)
    tree_b = AggregationNode(name="B", node_type="bi_aggregator", state=1)
    mock_connection.get_aggregations_states = AsyncMock(return_value={})
    mock_connection.get_aggregation_tree = AsyncMock(
        side_effect=lambda aid, depth: tree_a if aid == "A" else tree_b
    )
    monkeypatch.setattr(state_service, "_connections", {"mock": mock_connection})

    await state_service.get_board_states(cfg, auth_user=None)
    # Two distinct (id, depth) pairs even though "A" appears twice.
    assert mock_connection.get_aggregation_tree.await_count == 2
