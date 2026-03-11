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

    @abstractmethod
    async def is_available(self) -> bool:
        """Check whether the backend is reachable."""
        ...
