"""Topology wire schemas (Flow Board) — shared by the API layer and
state_service's delta computation, so the service layer never has to import
from the API layer."""

from __future__ import annotations

from pydantic import BaseModel

from app.schemas.state import ServicesSummary


class ServiceNode(BaseModel):
    name: str
    state: str
    output: str
    acknowledged: bool = False
    in_downtime: bool = False
    notifications_enabled: bool = True
    last_state_change: float | None = None
    last_check: float | None = None
    next_check: float | None = None


class TopologyNode(BaseModel):
    name: str
    parents: list[str]
    state: str
    output: str
    site_id: str | None = None
    services: list[ServiceNode] = []
    services_truncated_count: int = 0
    # Set when the host was outside the top-K affected hosts and its service
    # detail wasn't fetched. The donut ring (services_summary) is still
    # populated so the client can render an at-a-glance state aggregate.
    services_omitted: bool = False
    alias: str = ""
    address: str = ""
    acknowledged: bool = False
    in_downtime: bool = False
    notifications_enabled: bool = True
    active_checks_enabled: bool = True
    last_check: float | None = None
    next_check: float | None = None
    last_state_change: float | None = None
    state_type: str = ""
    current_attempt: int = 0
    max_attempts: int = 0
    services_summary: ServicesSummary | None = None


class ServiceTiming(BaseModel):
    name: str
    last_check: float | None = None
    next_check: float | None = None


class TopologyTiming(BaseModel):
    """Slim check-timing patch for a topology host (and its services).

    Mirrors ``ObjectTiming`` on the state channel: ``last_check``/``next_check``/
    ``current_attempt`` tick on every Checkmk re-check and are deliberately
    excluded from the topology change-hash (so a recheck doesn't flap every host
    as ``changed``). They travel here instead, keeping the Flow Board's
    next-check / overdue readouts live without re-sending whole nodes.
    """

    name: str
    last_check: float | None = None
    next_check: float | None = None
    current_attempt: int = 0
    services: list[ServiceTiming] = []


class TopologyDelta(BaseModel):
    """Incremental update for a Flow Board's topology snapshot.

    `full=True` carries the complete topology (initial connect / reset).
    Otherwise `added`/`changed`/`removed` are diffs against the previous tick:
    only hosts whose volatile fields actually changed appear in `changed`.
    `timing` carries check-timing-only patches for hosts not in `changed`.
    """

    full: bool
    generated_at: float
    added: list[TopologyNode] = []
    changed: list[TopologyNode] = []
    removed: list[str] = []
    timing: list[TopologyTiming] = []
