"""Aggregate monitoring states for board objects."""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable
from typing import TYPE_CHECKING

from app.connections.base import ServiceRow
from app.core.config import settings
from app.schemas.board import AggregationNode, BoardConfig, BoardObject, RadarView, WorldmapView
from app.schemas.state import MapStates, ObjectState, ServicesSummary

# Late import to avoid the connections-API module being imported at startup.
# TopologyNode lives there because it's the response_model of /topology;
# the snapshot diff helpers below are the only state_service consumers.
if TYPE_CHECKING:
    from app.api.v1.connections import TopologyDelta, TopologyNode

# Combined severity for cross-scale worst-state aggregation (recognize_services)
_COMBINED_SEVERITY: dict[str, int] = {
    "PENDING": -1,
    "UP": 0,
    "OK": 0,
    "UNREACHABLE": 1,
    "UNKNOWN": 1,
    "WARNING": 2,
    "DOWN": 3,
    "CRITICAL": 4,
}
_MONITORING_TYPES: frozenset[str] = frozenset(
    {"host", "service", "hostgroup", "servicegroup", "line", "graph"}
)
# Types that contribute to the worst-state roll-up of a map-link object.
# Includes map and aggregation so nested boards transitively show up in the
# parent map's status pill.
_MAP_AGGREGATION_TYPES: frozenset[str] = _MONITORING_TYPES | {"map", "aggregation"}

if TYPE_CHECKING:
    from app.connections.base import ConnectionBase

logger = logging.getLogger(__name__)

# In-memory registry of configured connections
_connections: dict[str, ConnectionBase] = {}


def register_connection(connection_id: str, connection: ConnectionBase) -> None:
    _connections[connection_id] = connection


def get_connection(connection_id: str) -> ConnectionBase | None:
    return _connections.get(connection_id)


def list_connection_ids() -> list[str]:
    return list(_connections.keys())


async def get_connection_objects(
    connection_id: str, obj_type: str, host: str | None = None
) -> list[str]:
    """Return available object names from a connection (for autocomplete)."""
    connection = get_connection(connection_id)
    if connection is None:
        return []
    raw = await connection.get_objects(obj_type)
    if obj_type == "service" and host:
        # raw items are "hostname;service_description" – filter and strip prefix
        prefix = f"{host};"
        return [item[len(prefix) :] for item in raw if item.startswith(prefix)]
    return raw


async def get_board_states(
    cfg: BoardConfig,
    auth_user: str | None = None,
    can_view_board: Callable[[str], bool] | None = None,
) -> MapStates:
    """Fetch current states for all objects in a board.

    When *auth_user* is provided and CHECKMK_OMD_ROOT is configured, Livestatus
    queries are scoped to that user's contact groups so they only see objects
    they are authorised for.
    """
    connection_id = cfg.connection_id
    connection = get_connection(connection_id)

    if connection is None:
        logger.warning("No connection registered for '%s'", connection_id)
        states = [
            ObjectState(object_id=obj.id, type=obj.type, state="PENDING") for obj in cfg.objects
        ]
        return MapStates(
            map_name=cfg.name, states=states, generated_at=time.time(), connection_ok=False
        )

    if (
        auth_user is not None
        and settings.checkmk_omd_root
        and hasattr(connection, "with_auth_user")
    ):
        async with connection.with_auth_user(auth_user):
            return await _execute_board_states(
                cfg, connection, auth_user=auth_user, can_view_board=can_view_board
            )
    return await _execute_board_states(cfg, connection, can_view_board=can_view_board)


async def _execute_board_states(
    cfg: BoardConfig,
    connection: ConnectionBase,
    auth_user: str | None = None,
    can_view_board: Callable[[str], bool] | None = None,
) -> MapStates:
    """Inner state-fetch implementation; must be called with auth context already set."""
    if cfg.view.type == "radar":
        return await _get_radar_states(cfg, connection)

    # Inflate worldmap automap-source hosts into transient board objects so
    # the rest of the pipeline (state fetch, websocket diffing, frontend
    # rendering) treats them like any other host. They are not persisted —
    # the BoardConfig in board_service still holds only the user-curated set.
    objects = await inflate_auto_objects(cfg, connection)

    state_map = await _states_for_objects(
        objects,
        default_connection=connection,
        default_connection_id=cfg.connection_id,
        auth_user=auth_user,
        can_view_board=can_view_board,
        visited_maps=frozenset({cfg.name}),
    )
    states = list(state_map.values())

    # Determine connection health using only monitoring-object states.
    # Non-monitoring types (image, textbox, map) always return PENDING without stale=True,
    # so including them would mask a genuinely unreachable connection.
    monitoring_states = [s for s in states if s.type in _MONITORING_TYPES]
    if monitoring_states:
        # Backend is considered down only if ALL monitoring queries raised exceptions (stale=True).
        connection_ok = not all(s.stale for s in monitoring_states)
    else:
        # No monitoring objects in this map – ping the connection explicitly.
        try:
            connection_ok = await connection.is_available()
        except Exception:
            connection_ok = False

    return MapStates(
        map_name=cfg.name, states=states, generated_at=time.time(), connection_ok=connection_ok
    )


_AUTO_PREFIX = "auto:"


async def inflate_auto_objects(cfg: BoardConfig, connection: ConnectionBase) -> list[BoardObject]:
    """If the board is a worldmap with ``auto_source``, append matching hosts.

    Persisted objects always win — if an auto-discovered host shares its name
    with one the operator manually placed, the manual entry's coordinates are
    kept and the auto entry is skipped, giving the operator a safe override.
    """
    view = cfg.view
    if not isinstance(view, WorldmapView) or view.auto_source is None:
        return cfg.objects
    group_type = view.auto_source if view.auto_source != "all_hosts" else None
    try:
        geo_hosts = await connection.get_hosts_with_geo(
            group_type=group_type,
            group_name=view.auto_filter_value or None,
        )
    except Exception:
        logger.warning("Failed to fetch geo hosts for board %s", cfg.name, exc_info=True)
        return cfg.objects

    existing_host_names = {o.host_name for o in cfg.objects if o.host_name}
    inflated: list[BoardObject] = list(cfg.objects)
    for h in geo_hosts:
        if h["name"] in existing_host_names:
            continue
        inflated.append(
            BoardObject(
                id=f"{_AUTO_PREFIX}{h['name']}",
                type="host",
                host_name=h["name"],
                lat=h["lat"],
                lng=h["lng"],
            )
        )
    return inflated


async def _states_for_objects(
    objects: list[BoardObject],
    *,
    default_connection: ConnectionBase,
    default_connection_id: str,
    auth_user: str | None = None,
    can_view_board: Callable[[str], bool] | None = None,
    board_cfg_cache: dict[str, BoardConfig | None] | None = None,
    visited_maps: frozenset[str] = frozenset(),
) -> dict[str, ObjectState]:
    """Run the batched state fetch once per distinct connection, then merge.

    NagVis maps allow ``backend_id`` per object so a single board can mix
    monitoring sources (Checkmk + Icinga, two CMK sites, …). We honour the
    same contract: an object's ``connection_id`` overrides the board default.
    Objects sharing a connection are still batched together — only the
    cross-connection split adds round-trips, which run in parallel.
    """
    if board_cfg_cache is None:
        board_cfg_cache = {}

    groups: dict[str, list[BoardObject]] = {}
    for obj in objects:
        cid = obj.connection_id or default_connection_id
        groups.setdefault(cid, []).append(obj)

    async def _run(cid: str, group_objs: list[BoardObject]) -> dict[str, ObjectState]:
        conn = default_connection if cid == default_connection_id else get_connection(cid)
        if conn is None:
            return {
                obj.id: ObjectState(object_id=obj.id, type=obj.type, state="PENDING", stale=True)
                for obj in group_objs
            }
        return await _get_board_states_batched(
            conn,
            group_objs,
            auth_user=auth_user,
            can_view_board=can_view_board,
            board_cfg_cache=board_cfg_cache,
            _visited_maps=visited_maps,
        )

    if len(groups) == 1:
        cid, group_objs = next(iter(groups.items()))
        return await _run(cid, group_objs)

    results = await asyncio.gather(*[_run(cid, objs) for cid, objs in groups.items()])
    merged: dict[str, ObjectState] = {}
    for r in results:
        merged.update(r)
    return merged


async def _get_board_states_batched(  # noqa: C901 — dispatches 7 object types inline; splitting hides intent
    connection: ConnectionBase,
    objects: list[BoardObject],
    auth_user: str | None = None,
    can_view_board: Callable[[str], bool] | None = None,
    board_cfg_cache: dict[str, BoardConfig | None] | None = None,
    _visited_maps: frozenset[str] | None = None,
) -> dict[str, ObjectState]:
    """Fetch states for all board objects using batch queries where supported.

    ``board_cfg_cache`` memoises ``board_service.get_board`` across the full
    map-link recursion so a board referenced by several sibling or nested maps
    loads only once. The cache stores ``None`` for not-found boards to avoid
    retrying missing names.

    ``_visited_maps`` carries the set of board names already on the current
    recursion path so map-link aggregation can transitively include nested
    maps without infinite-looping on cycles.
    """
    if board_cfg_cache is None:
        board_cfg_cache = {}
    if _visited_maps is None:
        _visited_maps = frozenset()
    hosts_soft: list[BoardObject] = []
    hosts_hard: list[BoardObject] = []
    svcs_soft: list[BoardObject] = []
    svcs_hard: list[BoardObject] = []
    lines: list[BoardObject] = []
    map_objects: list[BoardObject] = []
    aggregation_objs: list[BoardObject] = []
    others: list[BoardObject] = []

    for obj in objects:
        if obj.type == "host" and obj.host_name:
            (hosts_hard if obj.only_hard_states else hosts_soft).append(obj)
        elif obj.type == "service" and obj.host_name and obj.service_description:
            (svcs_hard if obj.only_hard_states else svcs_soft).append(obj)
        elif obj.type == "graph" and obj.host_name and obj.service_description:
            svcs_soft.append(obj)
        elif obj.type == "graph" and obj.host_name:
            hosts_soft.append(obj)
        elif obj.type == "line":
            lines.append(obj)
        elif obj.type == "map" and obj.map_name:
            map_objects.append(obj)
        elif obj.type == "aggregation" and obj.aggregation_id:
            aggregation_objs.append(obj)
        else:
            others.append(obj)

    results: dict[str, ObjectState] = {}

    for host_group, only_hard in [(hosts_soft, False), (hosts_hard, True)]:
        if not host_group:
            continue
        batch_ok = True
        try:
            batch = await connection.get_hosts_states(
                [o.host_name for o in host_group if o.host_name is not None],
                only_hard=only_hard,
            )
        except Exception:
            logger.warning("Batch host state query failed (only_hard=%s)", only_hard, exc_info=True)
            batch = {}
            batch_ok = False
        for obj in host_group:
            assert obj.host_name is not None
            if batch_ok and obj.host_name not in batch:
                # Permission-filtered batches return only the hosts a non-admin
                # user is allowed to see; for that user the missing entry is a
                # permission denial. For admin/SSO-admin context (auth_user is
                # None) the host is *actually* not present in monitoring data.
                state_value = "NO_PERMISSION" if auth_user is not None else "NOT_FOUND"
                results[obj.id] = ObjectState(object_id=obj.id, type="host", state=state_value)
            else:
                raw = batch.get(obj.host_name)
                s = (
                    ObjectState(**{**raw.model_dump(), "object_id": obj.id})
                    if raw is not None
                    else ObjectState(object_id=obj.id, type="host", state="PENDING", stale=True)
                )
                results[obj.id] = s

    host_objs = hosts_soft + hosts_hard
    summary_hosts = sorted(
        {
            o.host_name
            for o in host_objs
            if o.host_name is not None
            and results.get(o.id) is not None
            and results[o.id].state not in ("NO_PERMISSION", "NOT_FOUND")
        }
    )
    rs_objs = [
        o
        for o in host_objs
        if o.recognize_services
        and results.get(o.id) is not None
        and results[o.id].state != "NO_PERMISSION"
    ]
    rs_names = list({o.host_name for o in rs_objs if o.host_name is not None})

    # Run summary + recognize_services service-batch in parallel — both depend on
    # the host-state batch above but neither depends on the other.
    summary_task: asyncio.Task[dict[str, ServicesSummary]] | None = (
        asyncio.create_task(connection.get_services_summary(summary_hosts))
        if summary_hosts
        else None
    )
    rs_task: asyncio.Task[dict[str, list[ServiceRow]]] | None = (
        asyncio.create_task(connection.get_hosts_services_batch(rs_names)) if rs_objs else None
    )

    if summary_task is not None:
        try:
            summary_batch = await summary_task
        except Exception:
            logger.warning("Services-summary query failed", exc_info=True)
            summary_batch = {}
        for obj in host_objs:
            if obj.host_name is None:
                continue
            existing = results.get(obj.id)
            if existing is None:
                continue
            summary = summary_batch.get(obj.host_name)
            if summary is not None:
                results[obj.id] = existing.model_copy(update={"services_summary": summary})

    if rs_task is not None:
        try:
            rs_svc_batch = await rs_task
        except Exception:
            logger.warning("Batch host-services query failed", exc_info=True)
            rs_svc_batch = {}
        for obj in rs_objs:
            assert obj.host_name is not None
            results[obj.id] = _aggregate_host_with_services_from_data(
                results[obj.id],
                rs_svc_batch.get(obj.host_name, []),
            )

    for svc_group, only_hard in [(svcs_soft, False), (svcs_hard, True)]:
        if not svc_group:
            continue
        pairs = [
            (o.host_name, o.service_description)
            for o in svc_group
            if o.host_name is not None and o.service_description is not None
        ]
        batch_ok = True
        try:
            svc_batch = await connection.get_services_states(pairs, only_hard=only_hard)
        except Exception:
            logger.warning(
                "Batch service state query failed (only_hard=%s)", only_hard, exc_info=True
            )
            svc_batch = {}
            batch_ok = False
        for obj in svc_group:
            assert obj.host_name is not None and obj.service_description is not None
            key = (obj.host_name, obj.service_description)
            if batch_ok and key not in svc_batch:
                state_value = "NO_PERMISSION" if auth_user is not None else "NOT_FOUND"
                results[obj.id] = ObjectState(object_id=obj.id, type="service", state=state_value)
            else:
                raw = svc_batch.get(key)
                s = (
                    ObjectState(**{**raw.model_dump(), "object_id": obj.id})
                    if raw is not None
                    else ObjectState(object_id=obj.id, type="service", state="PENDING", stale=True)
                )
                results[obj.id] = s

    if aggregation_objs:
        aids = [o.aggregation_id for o in aggregation_objs if o.aggregation_id]
        try:
            aggr_batch = await connection.get_aggregations_states(aids)
        except Exception:
            logger.warning("Batch aggregation state query failed", exc_info=True)
            aggr_batch = {}

        # Tree-fetch deduplicated by (aggregation_id, depth) — multiple board
        # objects with the same aggregation+depth share one connection call.
        unique_keys: set[tuple[str, int]] = set()
        for o in aggregation_objs:
            if o.aggregation_id and o.expand_depth > 0:
                unique_keys.add((o.aggregation_id, o.expand_depth))
        tree_keys: list[tuple[str, int]] = sorted(unique_keys)
        tree_map: dict[tuple[str, int], AggregationNode] = {}
        if tree_keys:
            tasks = [connection.get_aggregation_tree(aid, depth) for aid, depth in tree_keys]
            trees = await asyncio.gather(*tasks, return_exceptions=True)
            for tree_key, tree in zip(tree_keys, trees, strict=True):
                if isinstance(tree, AggregationNode):
                    tree_map[tree_key] = tree
                elif isinstance(tree, BaseException):
                    logger.warning("Aggregation tree fetch failed for %r", tree_key, exc_info=tree)

        for obj in aggregation_objs:
            assert obj.aggregation_id is not None
            raw = aggr_batch.get(obj.aggregation_id)
            s = (
                ObjectState(**{**raw.model_dump(), "object_id": obj.id})
                if raw is not None
                else ObjectState(object_id=obj.id, type="aggregation", state="PENDING", stale=True)
            )
            if obj.expand_depth > 0:
                tree = tree_map.get((obj.aggregation_id, obj.expand_depth))
                if tree is not None:
                    s = s.model_copy(update={"tree": tree})
            results[obj.id] = s

    individual = [_get_object_state(connection, obj) for obj in lines + others]
    for state in await asyncio.gather(*individual):
        results[state.object_id] = state

    if map_objects:
        from app.services import board_service

        # Load each unique referenced board once (avoid N reads for N map-link objects)
        # Maps without view permission are recorded as None to produce NO_PERMISSION state.
        board_states: dict[str, dict[str, ObjectState] | None] = {}
        for map_name in {o.map_name for o in map_objects if o.map_name}:
            if can_view_board is not None and not can_view_board(map_name):
                board_states[map_name] = None
                continue
            if map_name not in board_cfg_cache:
                board_cfg_cache[map_name] = board_service.get_board(map_name)
            ref_cfg = board_cfg_cache[map_name]
            if ref_cfg is None:
                continue
            ref_backend = get_connection(ref_cfg.connection_id)
            if ref_backend is None:
                continue
            # Include nested map-objects in the recursion as long as they
            # don't form a cycle — otherwise a board with only nested links
            # would aggregate to PENDING even when its leaves have real states.
            child_visited = _visited_maps | {map_name}
            included_objs = [
                o
                for o in ref_cfg.objects
                if o.type != "map" or (o.map_name and o.map_name not in child_visited)
            ]
            try:
                board_states[map_name] = await _states_for_objects(
                    included_objs,
                    default_connection=ref_backend,
                    default_connection_id=ref_cfg.connection_id,
                    auth_user=auth_user,
                    board_cfg_cache=board_cfg_cache,
                    visited_maps=child_visited,
                )
            except Exception:
                pass
        for obj in map_objects:
            assert obj.map_name is not None
            entry = board_states.get(obj.map_name)
            if entry is None and obj.map_name in board_states:
                # Explicitly None → no permission for the referenced board
                results[obj.id] = ObjectState(object_id=obj.id, type="map", state="NO_PERMISSION")
                continue
            sub = entry or {}
            mon = [s for s in sub.values() if s.type in _MAP_AGGREGATION_TYPES]
            if mon:
                real = [s for s in mon if s.state != "NO_PERMISSION"]
                if not real:
                    results[obj.id] = ObjectState(
                        object_id=obj.id, type="map", state="NO_PERMISSION"
                    )
                else:
                    worst = max(real, key=lambda s: _COMBINED_SEVERITY.get(s.state, 0))
                    results[obj.id] = ObjectState(object_id=obj.id, type="map", state=worst.state)
            else:
                results[obj.id] = ObjectState(object_id=obj.id, type="map", state="PENDING")

    return results


def _aggregate_host_with_services_from_data(
    host_state: ObjectState, services: list[ServiceRow]
) -> ObjectState:
    """Aggregate a pre-fetched host state with its services (no I/O)."""
    if not services:
        return host_state
    all_states = [host_state.state] + [s.get("state", "PENDING") for s in services]
    worst = max(all_states, key=lambda s: _COMBINED_SEVERITY.get(s, 0))
    if worst == host_state.state:
        return host_state
    return ObjectState(
        object_id=host_state.object_id,
        type="host",
        state=worst,
        output=host_state.output,
        perf_data=host_state.perf_data,
        acknowledged=host_state.acknowledged,
        in_downtime=host_state.in_downtime,
    )


async def _get_object_state(connection: ConnectionBase, obj: BoardObject) -> ObjectState:
    try:
        if obj.type == "host" and obj.host_name:
            if obj.only_hard_states:
                state = await connection.get_host_hard_state(obj.host_name)
            else:
                state = await connection.get_host_state(obj.host_name)
            if obj.recognize_services:
                state = await _aggregate_host_with_services(connection, state, obj.host_name)
        elif obj.type == "service" and obj.host_name and obj.service_description:
            if obj.only_hard_states:
                state = await connection.get_service_hard_state(
                    obj.host_name, obj.service_description
                )
            else:
                state = await connection.get_service_state(obj.host_name, obj.service_description)
        elif obj.type == "hostgroup" and obj.group_name:
            state = await connection.get_hostgroup_states(obj.group_name)
        elif obj.type == "servicegroup" and obj.group_name:
            state = await connection.get_servicegroup_states(obj.group_name)
        elif obj.type == "line" and obj.host_name and obj.service_description:
            state = await connection.get_service_state(obj.host_name, obj.service_description)
        elif obj.type == "line" and obj.host_name:
            state = await connection.get_host_state(obj.host_name)
        elif obj.type == "graph" and obj.host_name and obj.service_description:
            state = await connection.get_service_state(obj.host_name, obj.service_description)
        elif obj.type == "graph" and obj.host_name:
            state = await connection.get_host_state(obj.host_name)
        elif obj.type == "aggregation" and obj.aggregation_id:
            state = await connection.get_aggregation_state(obj.aggregation_id)
        else:
            state = ObjectState(object_id=obj.id, type=obj.type, state="PENDING")
        state.object_id = obj.id
        return state
    except Exception as exc:
        logger.exception("Error fetching state for object %s: %s", obj.id, exc)
        return ObjectState(object_id=obj.id, type=obj.type, state="PENDING", stale=True)


async def _aggregate_host_with_services(
    connection: ConnectionBase, host_state: ObjectState, hostname: str
) -> ObjectState:
    """Aggregate host state with the worst state of all its services."""
    try:
        services = await connection.get_host_services(hostname)
    except Exception:
        return host_state
    return _aggregate_host_with_services_from_data(host_state, services)


async def _get_radar_states(cfg: BoardConfig, connection: ConnectionBase) -> MapStates:
    """Fetch states for all dynamically resolved radar map members."""
    rv = cfg.view if isinstance(cfg.view, RadarView) else RadarView()
    states: list[ObjectState] = []

    if rv.filter == "all_hosts":
        try:
            host_batch = await connection.get_all_hosts_states()
        except Exception:
            host_batch = {}
        # Operators expect to see the service-state breakdown when clicking a host
        # in the radar drawer — without this the chip row stays empty for radar
        # boards even though the data is one cheap query away.
        if host_batch:
            try:
                summaries = await connection.get_services_summary(list(host_batch.keys()))
            except Exception:
                summaries = {}
        else:
            summaries = {}
        for host, s in host_batch.items():
            s.object_id = host
            if s.services_summary is None and host in summaries:
                s.services_summary = summaries[host]
            states.append(s)
    elif rv.filter == "all_services":
        try:
            svc_batch_all = await connection.get_all_services_states()
        except Exception:
            svc_batch_all = {}
        for (host, svc), s in svc_batch_all.items():
            member_id = f"{host};{svc}"
            s.object_id = member_id
            states.append(s)
    else:
        members = await connection.get_group_members(rv.filter, rv.filter_value)
        if not members:
            return MapStates(
                map_name=cfg.name, states=[], generated_at=time.time(), connection_ok=True
            )
        host_members = [m for m in members if ";" not in m]
        svc_members: list[tuple[str, str, str]] = []
        for m in members:
            if ";" in m:
                host, svc = m.split(";", 1)
                svc_members.append((m, host, svc))

        if host_members:
            try:
                batch = await connection.get_hosts_states(host_members)
            except Exception:
                batch = {}
            try:
                summaries = await connection.get_services_summary(host_members)
            except Exception:
                summaries = {}
            for h in host_members:
                s = batch.get(h) or ObjectState(
                    object_id=h, type="host", state="PENDING", stale=True
                )
                s.object_id = h
                if s.services_summary is None and h in summaries:
                    s.services_summary = summaries[h]
                states.append(s)

        if svc_members:
            pairs = [(host, svc) for (_, host, svc) in svc_members]
            try:
                svc_batch = await connection.get_services_states(pairs)
            except Exception:
                svc_batch = {}
            for member_id, host, svc in svc_members:
                s = svc_batch.get((host, svc)) or ObjectState(
                    object_id=member_id, type="service", state="PENDING", stale=True
                )
                s.object_id = member_id
                states.append(s)

    connection_ok = bool(states) and not all(s.stale for s in states)
    return MapStates(
        map_name=cfg.name, states=states, generated_at=time.time(), connection_ok=connection_ok
    )


# ---------------------------------------------------------------------------
# Flow Board topology snapshots — used by the WebSocket broadcast loop to
# emit incremental updates instead of re-sending the full topology every tick.
# ---------------------------------------------------------------------------

# (board_name, auth_user) → (host_name → volatile-fields hash)
_topology_snapshots: dict[tuple[str, str | None], dict[str, int]] = {}


def _hash_topology_node(n: TopologyNode) -> int:
    """Hash only operationally-significant fields.

    Stable identity/topology fields (name, parents, alias, address) are
    excluded — they're carried in `added` payloads and don't trigger
    `changed` entries on their own.

    Excluded for delta purposes (still travel inside any node that *does*
    get re-sent, just don't trigger a re-send on their own):
    - ``last_check``/``next_check``/``current_attempt`` — tick every
      Checkmk re-check (often ~30 s) regardless of whether anything real
      changed. Including them makes every host flap as ``changed`` and
      defeats the delta.
    - ``output`` (host *and* per-service) — typically embeds live latency
      like ``"OK - 127.0.0.1 rta 0.022ms lost 0%"`` which churns every
      check. Output text is rarely the *operationally* interesting bit;
      state transitions are.
    """
    s = n.services_summary
    summary = (s.ok, s.warning, s.critical, s.unknown, s.pending) if s is not None else ()
    services = tuple((sv.name, sv.state) for sv in n.services)
    return hash(
        (
            n.state,
            n.last_state_change,
            n.acknowledged,
            n.in_downtime,
            n.notifications_enabled,
            n.active_checks_enabled,
            n.services_omitted,
            n.services_truncated_count,
            summary,
            services,
        )
    )


def compute_topology_delta(
    board_name: str,
    auth_user: str | None,
    current: list[TopologyNode],
    *,
    force_full: bool = False,
) -> TopologyDelta:
    """Diff `current` against the previous snapshot for (board_name, auth_user).

    Side effect: stores the new snapshot in `_topology_snapshots` so the next
    call returns deltas relative to this one.
    """
    from app.api.v1.connections import TopologyDelta as _TopologyDelta

    key = (board_name, auth_user)
    prev = _topology_snapshots.get(key)
    new_hashes = {n.name: _hash_topology_node(n) for n in current}

    if force_full or prev is None:
        _topology_snapshots[key] = new_hashes
        return _TopologyDelta(full=True, generated_at=time.time(), added=current)

    by_name = {n.name: n for n in current}
    added = [n for n in current if n.name not in prev]
    changed = [n for n in current if n.name in prev and new_hashes[n.name] != prev[n.name]]
    removed = [name for name in prev if name not in by_name]

    _topology_snapshots[key] = new_hashes
    return _TopologyDelta(
        full=False,
        generated_at=time.time(),
        added=added,
        changed=changed,
        removed=removed,
    )


def drop_topology_snapshot(board_name: str, auth_user: str | None = None) -> None:
    """Forget the snapshot for a board (call when broadcast loop ends or board is deleted).

    With `auth_user=None`, drops snapshots for *all* users of the board.
    """
    if auth_user is not None:
        _topology_snapshots.pop((board_name, auth_user), None)
        return
    for key in [k for k in _topology_snapshots if k[0] == board_name]:
        _topology_snapshots.pop(key, None)


# ---------------------------------------------------------------------------
# Object-state delta encoding for the WebSocket broadcast loop. Without this,
# every tick re-sends the full state map (~600 B per object × N objects × M
# clients × every state_refresh_interval). Most checks are unchanged tick to
# tick, so the delta is much smaller in steady state.
# ---------------------------------------------------------------------------

# (board_name, auth_user) → (object_id → volatile-fields hash)
_state_snapshots: dict[tuple[str, str | None], dict[str, int]] = {}


def _hash_object_state(s: ObjectState) -> int:
    """Hash only operationally-significant fields.

    Excluded from the change-detection hash (they still ride along inside any
    state that *does* get re-sent, just don't trigger a re-send on their own):
    - ``last_check``/``next_check``/``current_attempt`` — tick every Checkmk
      re-check regardless of whether anything real changed.
    - ``output`` — typically embeds live latency like ``"OK - rta 0.022ms"``
      that fluctuates every check; the operationally interesting bit is the
      state transition, not the text.

    ``perf_data`` *is* included because the frontend appends it to per-object
    metric history on every push — dropping it would freeze the live graphs.
    """
    summary = s.services_summary
    summary_t = (
        (summary.ok, summary.warning, summary.critical, summary.unknown, summary.pending)
        if summary is not None
        else ()
    )
    # AggregationNode is recursive and not directly tuple-hashable. Pydantic
    # JSON dump is fast (Rust core) and only runs for aggregation objects.
    tree_repr = s.tree.model_dump_json() if s.tree is not None else ""
    return hash(
        (
            s.state,
            s.perf_data,
            s.acknowledged,
            s.in_downtime,
            s.stale,
            s.notifications_enabled,
            s.active_checks_enabled,
            s.state_type,
            s.max_attempts,
            s.last_state_change,
            s.site_id,
            summary_t,
            tree_repr,
        )
    )


def compute_states_delta(
    board_name: str,
    auth_user: str | None,
    current: list[ObjectState],
    *,
    force_full: bool = False,
) -> tuple[list[ObjectState], list[str], bool]:
    """Diff `current` against the previous snapshot for (board, auth_user).

    Returns ``(states_to_send, removed_ids, full)``:
    - ``states_to_send``: full list when ``full=True``; else only added or changed entries
    - ``removed_ids``: object_ids no longer present (only meaningful when ``full=False``)
    - ``full``: ``True`` on first call (no prior snapshot) or when ``force_full=True``

    Side effect: stores the new hashes so the next call diffs against this.
    """
    key = (board_name, auth_user)
    prev = _state_snapshots.get(key)
    new_hashes = {s.object_id: _hash_object_state(s) for s in current}

    if force_full or prev is None:
        _state_snapshots[key] = new_hashes
        return current, [], True

    by_id = {s.object_id: s for s in current}
    to_send = [
        s
        for s in current
        if s.object_id not in prev or new_hashes[s.object_id] != prev[s.object_id]
    ]
    removed = [oid for oid in prev if oid not in by_id]
    _state_snapshots[key] = new_hashes
    return to_send, removed, False


def drop_states_snapshot(board_name: str, auth_user: str | None = None) -> None:
    """Forget the snapshot for a board (call when broadcast loop ends or board is deleted).

    With ``auth_user=None``, drops snapshots for *all* users of the board.
    """
    if auth_user is not None:
        _state_snapshots.pop((board_name, auth_user), None)
        return
    for key in [k for k in _state_snapshots if k[0] == board_name]:
        _state_snapshots.pop(key, None)
