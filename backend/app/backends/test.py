"""Test/demo backend that returns static sample data."""

from __future__ import annotations

import math

from app.backends.base import BackendBase, MetricHistoryResult, ServiceRow, TopologyRow
from app.schemas.state import ObjectState

_HOST_STATES = ["UP", "DOWN", "UNREACHABLE"]
_SERVICE_STATES = ["OK", "WARNING", "CRITICAL", "UNKNOWN"]

_DEMO_HOSTS = ["localhost", "router01", "switch01", "fileserver", "mailserver"]
_DEMO_SERVICES = ["HTTP", "PING", "Disk /", "Memory", "CPU Load", "SSH"]
_DEMO_HOSTGROUPS = ["linux-servers", "windows-servers", "network-devices"]
_DEMO_SERVICEGROUPS = ["web-services", "storage", "system-checks"]


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
        if obj_type == "hostgroup":
            return list(_DEMO_HOSTGROUPS)
        if obj_type == "servicegroup":
            return list(_DEMO_SERVICEGROUPS)
        return []

    async def get_group_members(self, group_type: str, group_name: str) -> list[str]:
        if group_type in ("all_services", "servicegroup"):
            return [f"{h};{s}" for h in _DEMO_HOSTS for s in _DEMO_SERVICES]
        return list(_DEMO_HOSTS)

    async def get_topology(self) -> list[TopologyRow]:
        return [
            TopologyRow(name="router01", parents=[], state="UP", output=""),
            TopologyRow(name="switch01", parents=["router01"], state="UP", output=""),
            TopologyRow(name="localhost", parents=["router01"], state="UP", output=""),
            TopologyRow(
                name="fileserver",
                parents=["switch01"],
                state="DOWN",
                output="Connection refused",
            ),
            TopologyRow(name="mailserver", parents=["switch01"], state="UP", output=""),
        ]

    async def get_host_services(self, hostname: str) -> list[ServiceRow]:
        result: list[ServiceRow] = []
        for svc in _DEMO_SERVICES:
            state = await self.get_service_state(hostname, svc)
            result.append(ServiceRow(name=svc, state=state.state, output=state.output))
        return result

    async def get_metric_history(
        self,
        host: str,
        service: str | None,
        start: int,
        end: int,
    ) -> MetricHistoryResult:
        """Generate synthetic time-varying metric history for development."""
        svc_key = f"{host}:{service or ''}"
        base_val = (abs(hash(f"{svc_key}val")) % 60 + 20) / 100  # 0.2 – 0.8

        step = max(60, (end - start) // 60)
        num_points = (end - start) // step

        # Determine metrics from service name (same logic as get_service_state)
        if service and ("CPU" in service or "Load" in service or "load" in service):
            metric_defs = [
                ("load1", 0.0, ""),
                ("load5", 1.0, ""),
                ("load15", 2.0, ""),
            ]
        elif service and ("Memory" in service or "Mem" in service):
            metric_defs = [("used", 0.0, "%")]
        elif service and "Disk" in service:
            metric_defs = [("used", 0.0, "%")]
        elif service and "HTTP" in service:
            metric_defs = [("time", 0.0, "ms")]
        elif service and "PING" in service.upper():
            metric_defs = [("rta", 0.0, "ms"), ("pl", math.pi, "%")]
        else:
            metric_defs = [("value", 0.0, "")]

        series: dict[str, list[tuple[float, float, str]]] = {}
        titles: dict[str, str] = {}
        for label, phase, unit in metric_defs:
            amplitude = base_val * 0.3
            points: list[tuple[float, float, str]] = []
            for j in range(num_points):
                ts = float(start + j * step)
                # Sine wave + slower trend + tiny noise
                wave = math.sin(ts / 600 + phase) * amplitude
                trend = math.sin(ts / 3600) * amplitude * 0.5
                noise = ((hash(f"{ts:.0f}{label}") % 200) - 100) / 10000
                value = round(max(0.0, base_val + wave + trend + noise), 4)
                points.append((ts, value, unit))
            series[label] = points
            titles[label] = " ".join(w.capitalize() for w in label.split("_"))

        return MetricHistoryResult(series=series, titles=titles)

    async def is_available(self) -> bool:
        return True
