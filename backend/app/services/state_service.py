"""Aggregate monitoring states for board objects."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING

from app.schemas.board import BoardConfig, BoardObject
from app.schemas.state import MapStates, ObjectState

if TYPE_CHECKING:
    from app.backends.base import BackendBase

logger = logging.getLogger(__name__)

# In-memory registry of configured backends
_backends: dict[str, "BackendBase"] = {}


def register_backend(backend_id: str, backend: "BackendBase") -> None:
    _backends[backend_id] = backend


def get_backend(backend_id: str) -> "BackendBase | None":
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
        return [item[len(prefix):] for item in raw if item.startswith(prefix)]
    return raw


async def get_board_states(cfg: BoardConfig) -> MapStates:
    """Fetch current states for all objects in a board."""
    backend_id = cfg.globals.backend_id
    backend = get_backend(backend_id)

    if backend is None:
        logger.warning("No backend registered for '%s'", backend_id)
        states = [
            ObjectState(object_id=obj.id, type=obj.type, state="PENDING")
            for obj in cfg.objects
        ]
        return MapStates(map_name=cfg.name, states=states, generated_at=time.time(), backend_ok=False)

    if cfg.globals.map_type == "radar":
        return await _get_radar_states(cfg, backend)

    tasks = [_get_object_state(backend, obj) for obj in cfg.objects]
    states = list(await asyncio.gather(*tasks))

    # Determine backend health using only monitoring-object states.
    # Non-monitoring types (shape, textbox, map) always return PENDING without stale=True,
    # so including them would mask a genuinely unreachable backend.
    _monitoring_types = {"host", "service", "hostgroup", "servicegroup", "line"}
    monitoring_states = [s for s in states if s.type in _monitoring_types]
    if monitoring_states:
        # Backend is considered down only if ALL monitoring queries raised exceptions (stale=True).
        backend_ok = not all(s.stale for s in monitoring_states)
    else:
        # No monitoring objects in this map – ping the backend explicitly.
        try:
            backend_ok = await backend.is_available()
        except Exception:
            backend_ok = False

    return MapStates(map_name=cfg.name, states=states, generated_at=time.time(), backend_ok=backend_ok)


async def _get_object_state(backend: "BackendBase", obj: BoardObject) -> ObjectState:
    try:
        if obj.type == "host" and obj.host_name:
            state = await backend.get_host_state(obj.host_name)
        elif obj.type == "service" and obj.host_name and obj.service_description:
            state = await backend.get_service_state(obj.host_name, obj.service_description)
        elif obj.type == "hostgroup" and obj.group_name:
            state = await backend.get_hostgroup_states(obj.group_name)
        elif obj.type == "servicegroup" and obj.group_name:
            state = await backend.get_servicegroup_states(obj.group_name)
        elif obj.type == "line" and obj.host_name and obj.service_description:
            state = await backend.get_service_state(obj.host_name, obj.service_description)
        elif obj.type == "line" and obj.host_name:
            state = await backend.get_host_state(obj.host_name)
        else:
            state = ObjectState(object_id=obj.id, type=obj.type, state="PENDING")
        state.object_id = obj.id
        return state
    except Exception as exc:
        logger.exception("Error fetching state for object %s: %s", obj.id, exc)
        return ObjectState(object_id=obj.id, type=obj.type, state="PENDING", stale=True)


async def _get_radar_states(cfg: "BoardConfig", backend: "BackendBase") -> MapStates:
    """Fetch states for all dynamically resolved radar map members."""
    members = await backend.get_group_members(cfg.globals.radar_type, cfg.globals.radar_value)
    if not members:
        return MapStates(map_name=cfg.name, states=[], generated_at=time.time(), backend_ok=True)

    tasks = []
    for member in members:
        if ";" in member:
            host, svc = member.split(";", 1)
            tasks.append(_get_virtual_service_state(backend, member, host, svc))
        else:
            tasks.append(_get_virtual_host_state(backend, member))

    states = list(await asyncio.gather(*tasks))
    backend_ok = not all(s.stale for s in states)
    return MapStates(map_name=cfg.name, states=states, generated_at=time.time(), backend_ok=backend_ok)


async def _get_virtual_host_state(backend: "BackendBase", hostname: str) -> ObjectState:
    try:
        state = await backend.get_host_state(hostname)
        state.object_id = hostname
        return state
    except Exception as exc:
        logger.exception("Radar: error fetching host state for %s: %s", hostname, exc)
        return ObjectState(object_id=hostname, type="host", state="PENDING", stale=True)


async def _get_virtual_service_state(backend: "BackendBase", member_id: str, host: str, svc: str) -> ObjectState:
    try:
        state = await backend.get_service_state(host, svc)
        state.object_id = member_id
        return state
    except Exception as exc:
        logger.exception("Radar: error fetching service state for %s/%s: %s", host, svc, exc)
        return ObjectState(object_id=member_id, type="service", state="PENDING", stale=True)
