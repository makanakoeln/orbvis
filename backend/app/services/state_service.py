"""Aggregate monitoring states for board objects."""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable
from typing import TYPE_CHECKING

from app.core.config import settings
from app.schemas.board import BoardConfig, BoardObject, RadarView
from app.schemas.state import MapStates, ObjectState

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

if TYPE_CHECKING:
    from app.backends.base import BackendBase

logger = logging.getLogger(__name__)

# In-memory registry of configured backends
_backends: dict[str, BackendBase] = {}


def register_backend(backend_id: str, backend: BackendBase) -> None:
    _backends[backend_id] = backend


def get_backend(backend_id: str) -> BackendBase | None:
    return _backends.get(backend_id)


async def get_backend_objects(backend_id: str, obj_type: str, host: str | None = None) -> list[str]:
    """Return available object names from a backend (for autocomplete)."""
    backend = get_backend(backend_id)
    if backend is None:
        return []
    raw = await backend.get_objects(obj_type)
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
    backend_id = cfg.backend_id
    backend = get_backend(backend_id)

    if backend is None:
        logger.warning("No backend registered for '%s'", backend_id)
        states = [
            ObjectState(object_id=obj.id, type=obj.type, state="PENDING") for obj in cfg.objects
        ]
        return MapStates(
            map_name=cfg.name, states=states, generated_at=time.time(), backend_ok=False
        )

    if auth_user is not None and settings.checkmk_omd_root and hasattr(backend, "with_auth_user"):
        async with backend.with_auth_user(auth_user):
            return await _execute_board_states(
                cfg, backend, auth_user=auth_user, can_view_board=can_view_board
            )
    return await _execute_board_states(cfg, backend, can_view_board=can_view_board)


async def _execute_board_states(
    cfg: BoardConfig,
    backend: BackendBase,
    auth_user: str | None = None,
    can_view_board: Callable[[str], bool] | None = None,
) -> MapStates:
    """Inner state-fetch implementation; must be called with auth context already set."""
    if cfg.view.type == "radar":
        return await _get_radar_states(cfg, backend)

    state_map = await _get_board_states_batched(
        backend, cfg.objects, auth_user=auth_user, can_view_board=can_view_board
    )
    states = list(state_map.values())

    # Determine backend health using only monitoring-object states.
    # Non-monitoring types (image, textbox, map) always return PENDING without stale=True,
    # so including them would mask a genuinely unreachable backend.
    monitoring_states = [s for s in states if s.type in _MONITORING_TYPES]
    if monitoring_states:
        # Backend is considered down only if ALL monitoring queries raised exceptions (stale=True).
        backend_ok = not all(s.stale for s in monitoring_states)
    else:
        # No monitoring objects in this map – ping the backend explicitly.
        try:
            backend_ok = await backend.is_available()
        except Exception:
            backend_ok = False

    return MapStates(
        map_name=cfg.name, states=states, generated_at=time.time(), backend_ok=backend_ok
    )


async def _get_board_states_batched(
    backend: BackendBase,
    objects: list[BoardObject],
    auth_user: str | None = None,
    can_view_board: Callable[[str], bool] | None = None,
) -> dict[str, ObjectState]:
    """Fetch states for all board objects using batch queries where supported."""
    hosts_soft: list[BoardObject] = []
    hosts_hard: list[BoardObject] = []
    svcs_soft: list[BoardObject] = []
    svcs_hard: list[BoardObject] = []
    lines: list[BoardObject] = []
    map_objects: list[BoardObject] = []
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
        else:
            others.append(obj)

    results: dict[str, ObjectState] = {}

    for host_group, only_hard in [(hosts_soft, False), (hosts_hard, True)]:
        if not host_group:
            continue
        batch_ok = True
        try:
            batch = await backend.get_hosts_states(
                [o.host_name for o in host_group if o.host_name is not None],
                only_hard=only_hard,
            )
        except Exception:
            logger.warning("Batch host state query failed (only_hard=%s)", only_hard, exc_info=True)
            batch = {}
            batch_ok = False
        for obj in host_group:
            assert obj.host_name is not None
            if batch_ok and auth_user is not None and obj.host_name not in batch:
                results[obj.id] = ObjectState(object_id=obj.id, type="host", state="NO_PERMISSION")
            else:
                raw = batch.get(obj.host_name)
                s = (
                    ObjectState(**{**raw.model_dump(), "object_id": obj.id})
                    if raw is not None
                    else ObjectState(object_id=obj.id, type="host", state="PENDING", stale=True)
                )
                results[obj.id] = s

    rs_objs = [
        o
        for o in hosts_soft + hosts_hard
        if o.recognize_services
        and results.get(o.id) is not None
        and results[o.id].state != "NO_PERMISSION"
    ]
    if rs_objs:
        rs_names = list({o.host_name for o in rs_objs if o.host_name is not None})
        try:
            rs_svc_batch = await backend.get_hosts_services_batch(rs_names)
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
            svc_batch = await backend.get_services_states(pairs, only_hard=only_hard)
        except Exception:
            logger.warning(
                "Batch service state query failed (only_hard=%s)", only_hard, exc_info=True
            )
            svc_batch = {}
            batch_ok = False
        for obj in svc_group:
            assert obj.host_name is not None and obj.service_description is not None
            key = (obj.host_name, obj.service_description)
            if batch_ok and auth_user is not None and key not in svc_batch:
                results[obj.id] = ObjectState(
                    object_id=obj.id, type="service", state="NO_PERMISSION"
                )
            else:
                raw = svc_batch.get(key)
                s = (
                    ObjectState(**{**raw.model_dump(), "object_id": obj.id})
                    if raw is not None
                    else ObjectState(object_id=obj.id, type="service", state="PENDING", stale=True)
                )
                results[obj.id] = s

    individual = [_get_object_state(backend, obj) for obj in lines + others]
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
            ref_cfg = board_service.get_board(map_name)
            if ref_cfg is None:
                continue
            ref_backend = get_backend(ref_cfg.backend_id)
            if ref_backend is None:
                continue
            non_map_objs = [o for o in ref_cfg.objects if o.type != "map"]
            try:
                board_states[map_name] = await _get_board_states_batched(
                    ref_backend, non_map_objs, auth_user=auth_user
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
            mon = [s for s in sub.values() if s.type in _MONITORING_TYPES]
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
    host_state: ObjectState, services: list[dict]
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


async def _get_object_state(backend: BackendBase, obj: BoardObject) -> ObjectState:
    try:
        if obj.type == "host" and obj.host_name:
            if obj.only_hard_states:
                state = await backend.get_host_hard_state(obj.host_name)
            else:
                state = await backend.get_host_state(obj.host_name)
            if obj.recognize_services:
                state = await _aggregate_host_with_services(backend, state, obj.host_name)
        elif obj.type == "service" and obj.host_name and obj.service_description:
            if obj.only_hard_states:
                state = await backend.get_service_hard_state(obj.host_name, obj.service_description)
            else:
                state = await backend.get_service_state(obj.host_name, obj.service_description)
        elif obj.type == "hostgroup" and obj.group_name:
            state = await backend.get_hostgroup_states(obj.group_name)
        elif obj.type == "servicegroup" and obj.group_name:
            state = await backend.get_servicegroup_states(obj.group_name)
        elif obj.type == "line" and obj.host_name and obj.service_description:
            state = await backend.get_service_state(obj.host_name, obj.service_description)
        elif obj.type == "line" and obj.host_name:
            state = await backend.get_host_state(obj.host_name)
        elif obj.type == "graph" and obj.host_name and obj.service_description:
            state = await backend.get_service_state(obj.host_name, obj.service_description)
        elif obj.type == "graph" and obj.host_name:
            state = await backend.get_host_state(obj.host_name)
        else:
            state = ObjectState(object_id=obj.id, type=obj.type, state="PENDING")
        state.object_id = obj.id
        return state
    except Exception as exc:
        logger.exception("Error fetching state for object %s: %s", obj.id, exc)
        return ObjectState(object_id=obj.id, type=obj.type, state="PENDING", stale=True)


async def _aggregate_host_with_services(
    backend: BackendBase, host_state: ObjectState, hostname: str
) -> ObjectState:
    """Aggregate host state with the worst state of all its services."""
    try:
        services = await backend.get_host_services(hostname)
    except Exception:
        return host_state
    return _aggregate_host_with_services_from_data(host_state, services)


async def _get_radar_states(cfg: BoardConfig, backend: BackendBase) -> MapStates:
    """Fetch states for all dynamically resolved radar map members."""
    rv = cfg.view if isinstance(cfg.view, RadarView) else RadarView()
    members = await backend.get_group_members(rv.filter, rv.filter_value)
    if not members:
        return MapStates(map_name=cfg.name, states=[], generated_at=time.time(), backend_ok=True)

    host_members = [m for m in members if ";" not in m]
    svc_members: list[tuple[str, str, str]] = []
    for m in members:
        if ";" in m:
            host, svc = m.split(";", 1)
            svc_members.append((m, host, svc))

    states: list[ObjectState] = []

    if host_members:
        try:
            batch = await backend.get_hosts_states(host_members)
        except Exception:
            batch = {}
        for h in host_members:
            s = batch.get(h) or ObjectState(object_id=h, type="host", state="PENDING", stale=True)
            s.object_id = h
            states.append(s)

    if svc_members:
        pairs = [(host, svc) for (_, host, svc) in svc_members]
        try:
            svc_batch = await backend.get_services_states(pairs)
        except Exception:
            svc_batch = {}
        for member_id, host, svc in svc_members:
            s = svc_batch.get((host, svc)) or ObjectState(
                object_id=member_id, type="service", state="PENDING", stale=True
            )
            s.object_id = member_id
            states.append(s)

    backend_ok = not all(s.stale for s in states)
    return MapStates(
        map_name=cfg.name, states=states, generated_at=time.time(), backend_ok=backend_ok
    )
