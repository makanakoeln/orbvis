"""Abstract monitoring backend interface."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.schemas.state import ObjectState


class BackendBase(ABC):
    """Base class all monitoring backends must implement."""

    backend_id: str = "unknown"

    @abstractmethod
    async def get_host_state(self, hostname: str) -> ObjectState:
        """Return current state for a host."""
        ...

    @abstractmethod
    async def get_service_state(self, host: str, service: str) -> ObjectState:
        """Return current state for a service."""
        ...

    @abstractmethod
    async def get_hostgroup_states(self, group: str) -> ObjectState:
        """Return aggregated state for a host group (worst-state aggregation)."""
        ...

    @abstractmethod
    async def get_servicegroup_states(self, group: str) -> ObjectState:
        """Return aggregated state for a service group."""
        ...

    @abstractmethod
    async def get_objects(self, obj_type: str) -> list[str]:
        """Return list of object names of given type (host/service/hostgroup/…)."""
        ...

    @abstractmethod
    async def get_group_members(self, group_type: str, group_name: str) -> list[str]:
        """Return member names for a radar filter (hostgroup/servicegroup/all_hosts/all_services)."""
        ...

    @abstractmethod
    async def get_topology(self) -> list[dict]:
        """Return host topology as [{name, parents, state, output}] for automap."""
        ...

    @abstractmethod
    async def get_host_services(self, hostname: str) -> list[dict]:
        """Return services for a host as [{name, state, output}]."""
        ...

    async def get_host_hard_state(self, hostname: str) -> ObjectState:
        """Return the last hard state for a host (default: delegates to current state)."""
        return await self.get_host_state(hostname)

    async def get_service_hard_state(self, host: str, service: str) -> ObjectState:
        """Return the last hard state for a service (default: delegates to current state)."""
        return await self.get_service_state(host, service)

    async def get_hosts_states(
        self, hostnames: list[str], only_hard: bool = False
    ) -> dict[str, ObjectState]:
        """Return states for multiple hosts. Default: one call per host."""
        results: dict[str, ObjectState] = {}
        for h in hostnames:
            results[h] = await (
                self.get_host_hard_state(h) if only_hard else self.get_host_state(h)
            )
        return results

    async def get_services_states(
        self, pairs: list[tuple[str, str]], only_hard: bool = False
    ) -> dict[tuple[str, str], ObjectState]:
        """Return states for multiple (host, service) pairs. Default: one call per pair."""
        results: dict[tuple[str, str], ObjectState] = {}
        for host, svc in pairs:
            results[(host, svc)] = await (
                self.get_service_hard_state(host, svc)
                if only_hard
                else self.get_service_state(host, svc)
            )
        return results

    async def get_hosts_services_batch(self, hostnames: list[str]) -> dict[str, list[dict]]:
        """Return all services for multiple hosts. Default: one call per host."""
        results: dict[str, list[dict]] = {}
        for h in hostnames:
            results[h] = await self.get_host_services(h)
        return results

    async def get_host_geo(self, hostname: str) -> tuple[float, float] | None:
        """Return (lat, lng) from orbvis_lat/orbvis_lng host labels, or None if not set."""
        return None

    async def get_metric_history(
        self,
        host: str,
        service: str | None,
        start: int,
        end: int,
    ) -> dict[str, list[tuple[float, float, str]]]:
        """Return historical metric data as {label: [(ts, value, unit), ...]}.

        Default implementation returns empty dict (not all backends support this).
        Checkmk/Livestatus backends override this using the rrddata column.
        """
        return {}

    @abstractmethod
    async def is_available(self) -> bool:
        """Check whether the backend is reachable."""
        ...
