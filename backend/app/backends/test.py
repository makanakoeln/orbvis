"""Test/demo backend that returns static sample data."""

from __future__ import annotations


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
        val = abs(hash(f"{host}:{service}val")) % 91 + 5
        if "CPU" in service or "Load" in service:
            perf_data = f"load={val}.0;80;90;0;100"
        elif "Memory" in service or "Mem" in service:
            perf_data = f"used={val}%;80;90;0;100"
        elif "Disk" in service:
            perf_data = f"used={val}%;80;90;0;100"
        elif "HTTP" in service:
            ms = abs(hash(f"{host}:{service}ms")) % 2000 + 50
            perf_data = f"time={ms}ms;1000;3000;0;5000"
        elif "PING" in service.upper():
            rta = abs(hash(f"{host}:{service}rta")) % 200 + 1
            perf_data = f"rta={rta}.0ms;200;500;0; pl=0%;20;60;0;100"
        else:
            perf_data = f"value={val};80;90;0;100"
        return ObjectState(
            object_id="",
            type="service",
            state=state,
            output=f"Test output for {host}/{service}: {state}",
            perf_data=perf_data,
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

    async def get_group_members(self, group_type: str, group_name: str) -> list[str]:
        if group_type in ("all_services", "servicegroup"):
            return [f"{h};{s}" for h in _DEMO_HOSTS for s in _DEMO_SERVICES]
        return list(_DEMO_HOSTS)

    async def get_topology(self) -> list[dict]:
        return [
            {"name": "router01",    "parents": [],           "state": "UP",   "output": ""},
            {"name": "switch01",    "parents": ["router01"], "state": "UP",   "output": ""},
            {"name": "localhost",   "parents": ["router01"], "state": "UP",   "output": ""},
            {"name": "fileserver",  "parents": ["switch01"], "state": "DOWN", "output": "Connection refused"},
            {"name": "mailserver",  "parents": ["switch01"], "state": "UP",   "output": ""},
        ]

    async def is_available(self) -> bool:
        return True
