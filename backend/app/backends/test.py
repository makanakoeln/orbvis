"""Test/demo backend that returns static sample data."""

from __future__ import annotations

import random

from app.backends.base import BackendBase
from app.schemas.state import ObjectState

_HOST_STATES = ["UP", "DOWN", "UNREACHABLE"]
_SERVICE_STATES = ["OK", "WARNING", "CRITICAL", "UNKNOWN"]

_DEMO_HOSTS = ["localhost", "router01", "switch01", "fileserver", "mailserver"]
_DEMO_SERVICES = ["HTTP", "PING", "Disk /", "Memory", "CPU Load", "SSH"]


class TestBackend(BackendBase):
    """Returns deterministic demo states for testing."""

    backend_id = "test"

    async def get_host_state(self, hostname: str) -> ObjectState:
        # Deterministic based on hostname hash
        idx = hash(hostname) % len(_HOST_STATES)
        state = _HOST_STATES[idx]
        return ObjectState(
            object_id="",  # will be overwritten by state_service
            type="host",
            state=state,
            output=f"Test output for {hostname}: {state}",
            acknowledged=False,
            in_downtime=False,
        )

    async def get_service_state(self, host: str, service: str) -> ObjectState:
        idx = hash(f"{host}:{service}") % len(_SERVICE_STATES)
        state = _SERVICE_STATES[idx]
        return ObjectState(
            object_id="",
            type="service",
            state=state,
            output=f"Test output for {host}/{service}: {state}",
            acknowledged=False,
            in_downtime=False,
        )

    async def get_hostgroup_states(self, group: str) -> ObjectState:
        idx = hash(group) % len(_HOST_STATES)
        state = _HOST_STATES[idx]
        return ObjectState(
            object_id="",
            type="hostgroup",
            state=state,
            output=f"Hostgroup {group}: {state}",
        )

    async def get_servicegroup_states(self, group: str) -> ObjectState:
        idx = hash(group) % len(_SERVICE_STATES)
        state = _SERVICE_STATES[idx]
        return ObjectState(
            object_id="",
            type="servicegroup",
            state=state,
            output=f"Servicegroup {group}: {state}",
        )

    async def get_objects(self, obj_type: str) -> list[str]:
        if obj_type == "host":
            return list(_DEMO_HOSTS)
        if obj_type == "service":
            return [f"{h};{s}" for h in _DEMO_HOSTS for s in _DEMO_SERVICES]
        return []

    async def is_available(self) -> bool:
        return True
