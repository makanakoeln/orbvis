"""Aggregate monitoring states for map objects."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING

from app.schemas.map import MapConfig, MapObject
from app.schemas.state import ObjectState, MapStates

if TYPE_CHECKING:
    from app.backends.base import BackendBase

logger = logging.getLogger(__name__)

# In-memory registry of configured backends
_backends: dict[str, "BackendBase"] = {}


def register_backend(backend_id: str, backend: "BackendBase") -> None:
    _backends[backend_id] = backend


def get_backend(backend_id: str) -> "BackendBase | None":
    return _backends.get(backend_id)


async def get_map_states(cfg: MapConfig) -> MapStates:
    """Fetch current states for all objects in a map."""
    backend_id = cfg.globals.backend_id
    backend = get_backend(backend_id)

    if backend is None:
        logger.warning("No backend registered for '%s'", backend_id)
        states = [
            ObjectState(object_id=obj.id, type=obj.type, state="PENDING")
            for obj in cfg.objects
        ]
        return MapStates(map_name=cfg.name, states=states, generated_at=time.time())

    tasks = [_get_object_state(backend, obj) for obj in cfg.objects]
    states = list(await asyncio.gather(*tasks))
    return MapStates(map_name=cfg.name, states=states, generated_at=time.time())


async def _get_object_state(backend: "BackendBase", obj: MapObject) -> ObjectState:
    try:
        if obj.type == "host" and obj.host_name:
            state = await backend.get_host_state(obj.host_name)
        elif obj.type == "service" and obj.host_name and obj.service_description:
            state = await backend.get_service_state(obj.host_name, obj.service_description)
        elif obj.type == "hostgroup" and obj.group_name:
            state = await backend.get_hostgroup_states(obj.group_name)
        elif obj.type == "servicegroup" and obj.group_name:
            state = await backend.get_servicegroup_states(obj.group_name)
        else:
            state = ObjectState(object_id=obj.id, type=obj.type, state="PENDING")
        state.object_id = obj.id
        return state
    except Exception as exc:
        logger.exception("Error fetching state for object %s: %s", obj.id, exc)
        return ObjectState(object_id=obj.id, type=obj.type, state="PENDING", stale=True)
