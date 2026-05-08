"""Connection configuration API."""

from __future__ import annotations

import asyncio
import logging
import re
import time
from dataclasses import dataclass

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.api.v1.deps import get_current_user, require_admin, resolve_auth_user
from app.connections.base import ConnectionBase, ServiceRow, TopologyRow, topology_problem_rank
from app.core.config import settings
from app.integrations import checkmk as cmk_integration
from app.models.user import User
from app.schemas.board import AggregationInfo
from app.schemas.connection import (
    REDACTED_SECRET,
    ConnectionConfig,
    ConnectionCreate,
    ConnectionUpdate,
    _redact,
)
from app.schemas.state import ObjectDetails, ServicesSummary
from app.services import connection_service
from app.services.state_service import get_connection, get_connection_objects

logger = logging.getLogger(__name__)
router = APIRouter()


class TestResult(BaseModel):
    ok: bool
    message: str


@router.get("", response_model=list[ConnectionConfig])
async def list_backends(_: User = Depends(require_admin)) -> list[ConnectionConfig]:
    return [_redact(b) for b in connection_service.load_all()]


@router.post("", response_model=ConnectionConfig, status_code=status.HTTP_201_CREATED)
async def create_backend(
    data: ConnectionCreate, _: User = Depends(require_admin)
) -> ConnectionConfig:
    if REDACTED_SECRET in (data.automation_secret, data.icinga2_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide a real secret value when creating a connection",
        )
    try:
        return _redact(connection_service.create(data))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from None


@router.put("/{connection_id}", response_model=ConnectionConfig)
async def update_backend(
    connection_id: str,
    data: ConnectionUpdate,
    _: User = Depends(require_admin),
) -> ConnectionConfig:
    existing = next((b for b in connection_service.load_all() if b.id == connection_id), None)
    if existing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connection not found")

    payload = data.model_dump()
    # Frontend echoes the redaction sentinel back unchanged when the admin did
    # not retype the secret — keep the previously stored value in that case.
    if payload.get("automation_secret") == REDACTED_SECRET:
        payload["automation_secret"] = existing.automation_secret
    if payload.get("icinga2_password") == REDACTED_SECRET:
        payload["icinga2_password"] = existing.icinga2_password

    updated = ConnectionConfig(id=connection_id, **payload)
    result = connection_service.update(connection_id, updated)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connection not found")
    _invalidate_topology_cache(connection_id)
    return _redact(result)


@router.delete("/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_backend(connection_id: str, _: User = Depends(require_admin)) -> None:
    if not connection_service.delete(connection_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connection not found")
    _invalidate_topology_cache(connection_id)


class ConnectionContext(BaseModel):
    monitoring_core: str | None  # 'cmc', 'nagios', or None
    omd_site: str | None


@router.get("/{connection_id}/context", response_model=ConnectionContext)
async def get_backend_context(
    connection_id: str, _: User = Depends(require_admin)
) -> ConnectionContext:
    """Return OMD/CMC context for the connection settings UI.

    Only meaningful for Livestatus connections inside an OMD site. Returns nulls
    for non-OMD setups. The connection_id is accepted for future multi-site use;
    currently core detection is always local.
    """
    return ConnectionContext(
        monitoring_core=cmk_integration.get_monitoring_core(),
        omd_site=settings.checkmk_site or None,
    )


@router.get("/{connection_id}/test", response_model=TestResult)
async def test_backend(connection_id: str, _: User = Depends(require_admin)) -> TestResult:
    """Test connectivity of a saved connection."""
    connection = get_connection(connection_id)
    if connection is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection not registered (restart needed?)",
        )
    try:
        ok = await connection.is_available()
        return TestResult(
            ok=ok, message="Connection successful" if ok else "Connection not reachable"
        )
    except Exception as exc:
        return TestResult(ok=False, message=str(exc))


@router.post("/test-connection", response_model=TestResult)
async def test_connection(data: ConnectionCreate, _: User = Depends(require_admin)) -> TestResult:
    """Test connection details without saving – used by the create/edit dialog."""
    try:
        connection = connection_service.build_instance(data)
        ok = await connection.is_available()
        return TestResult(
            ok=ok, message="Connection successful" if ok else "Connection not reachable"
        )
    except Exception as exc:
        return TestResult(ok=False, message=str(exc))


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


class TopologyDelta(BaseModel):
    """Incremental update for a Flow Board's topology snapshot.

    `full=True` carries the complete topology (initial connect / reset).
    Otherwise `added`/`changed`/`removed` are diffs against the previous tick:
    only hosts whose volatile fields actually changed appear in `changed`.
    """

    full: bool
    generated_at: float
    added: list[TopologyNode] = []
    changed: list[TopologyNode] = []
    removed: list[str] = []


# Higher number = more "interesting"; OK comes last, PENDING/unknown stable in
# the middle so a flapping service doesn't reshuffle the visible top-N.
_SERVICE_SORT_KEY = {"CRITICAL": 0, "WARNING": 1, "UNKNOWN": 2, "PENDING": 3, "OK": 4}


def _sorted_truncated_services(svcs: list[ServiceRow], limit: int) -> tuple[list[ServiceRow], int]:
    """Return (top-N services, truncated_count). Non-OK first, then OK alphabetic."""
    ordered = sorted(
        svcs,
        key=lambda s: (_SERVICE_SORT_KEY.get(s["state"], 5), s["name"]),
    )
    if limit <= 0 or len(ordered) <= limit:
        return ordered, 0
    return ordered[:limit], len(ordered) - limit


# Topology cache: short TTL so concurrent browser tabs share a single
# Livestatus round-trip. Reuses the TTL/eviction shape from
# LivestatusConnection._services_summary_cache (livestatus.py:567+).
@dataclass(frozen=True)
class _TopologyCacheKey:
    connection_id: str
    root: str | None
    child_layers: int | None
    parent_layers: int | None
    include_services: bool
    services_per_host: int
    top_affected_hosts: int
    auth_user: str | None


_topology_cache: dict[_TopologyCacheKey, tuple[float, list[TopologyNode]]] = {}
# Per-key locks dedupe in-flight fetches: if N tabs cache-miss simultaneously
# only the first runs the query, the rest await the same result.
_topology_cache_locks: dict[_TopologyCacheKey, asyncio.Lock] = {}
_TOPOLOGY_CACHE_MAX = 32


def _drop_topology_cache_key(key: _TopologyCacheKey) -> None:
    _topology_cache.pop(key, None)
    _topology_cache_locks.pop(key, None)


def _invalidate_topology_cache(connection_id: str | None = None) -> None:
    """Drop cached topology entries (optionally scoped to one connection_id)."""
    keys = [k for k in _topology_cache if connection_id is None or k.connection_id == connection_id]
    for k in keys:
        _drop_topology_cache_key(k)


def _filter_topology(
    nodes: list[TopologyRow],
    root: str | None,
    child_layers: int | None,
    parent_layers: int | None,
) -> list[TopologyRow]:
    if not root:
        return nodes
    by_name: dict[str, TopologyRow] = {n["name"]: n for n in nodes}
    if root not in by_name:
        return []

    children_of: dict[str, list[str]] = {}
    parents_of: dict[str, list[str]] = {}
    for n in nodes:
        parents = n.get("parents") or []
        parents_of[n["name"]] = list(parents)
        for parent in parents:
            children_of.setdefault(parent, []).append(n["name"])

    def bfs(neighbours: dict[str, list[str]], depth_limit: int) -> set[str]:
        seen: set[str] = {root}
        frontier: list[str] = [root]
        depth = 0
        while frontier and (depth_limit < 0 or depth < depth_limit):
            depth += 1
            nxt: list[str] = []
            for name in frontier:
                for nb in neighbours.get(name, []):
                    if nb not in seen and nb in by_name:
                        seen.add(nb)
                        nxt.append(nb)
            frontier = nxt
        return seen

    keep = bfs(children_of, child_layers if child_layers is not None else -1)
    keep |= bfs(parents_of, parent_layers if parent_layers is not None else 0)
    return [n for n in nodes if n["name"] in keep]


# Local alias for the shared rank helper — keeps intra-file usage readable
# without re-exporting the longer name.
_problem_count = topology_problem_rank


async def build_topology_response(
    connection: ConnectionBase,
    *,
    include_services: bool,
    services_per_host: int,
    top_affected_hosts: int,
    root: str | None = None,
    child_layers: int | None = None,
    parent_layers: int | None = None,
) -> list[TopologyNode]:
    """Fetch topology + (optionally) per-host services and return TopologyNodes.

    Shared between the REST endpoint and the WS broadcast loop so both produce
    identical payloads. Caller is responsible for any auth_user context and
    caching — this helper just runs the queries.
    """
    rows = await connection.get_topology()
    rows = _filter_topology(rows, root, child_layers, parent_layers)

    if not (include_services and rows):
        return [TopologyNode(**r) for r in rows]

    if top_affected_hosts <= 0:
        affected: set[str] = set()
    elif len(rows) > top_affected_hosts:
        ranked = sorted(rows, key=_problem_count, reverse=True)
        affected = {r["name"] for r in ranked[:top_affected_hosts]}
    else:
        affected = {r["name"] for r in rows}

    services_by_host = (
        await connection.get_hosts_services_batch(sorted(affected)) if affected else {}
    )

    result: list[TopologyNode] = []
    for row in rows:
        if row["name"] not in affected:
            result.append(TopologyNode(**row, services_omitted=True))
            continue
        svcs = list(services_by_host.get(row["name"], []))
        kept, truncated = _sorted_truncated_services(svcs, services_per_host)
        result.append(
            TopologyNode(
                **row,
                services=[ServiceNode.model_validate(s) for s in kept],
                services_truncated_count=truncated,
            )
        )
    return result


@router.get("/{connection_id}/topology", response_model=list[TopologyNode])
async def get_topology(
    connection_id: str,
    include_services: bool = Query(False),
    root: str | None = Query(None),
    child_layers: int | None = Query(None, ge=-1, le=20),
    parent_layers: int | None = Query(None, ge=-1, le=20),
    services_per_host: int | None = Query(None, ge=0, le=500),
    top_affected_hosts: int | None = Query(None, ge=0, le=1000),
    current_user: User = Depends(get_current_user),
) -> list[TopologyNode]:
    """Return host topology for flow board rendering.

    For ``include_services=True`` only the top-K hosts (ranked by problem
    count, default ``settings.flow_board_top_affected_hosts``) are bulk-fetched
    via ``get_hosts_services_batch``; their per-host service list is capped by
    ``services_per_host``/``settings.flow_board_max_services_per_host`` and the
    surplus reported as ``services_truncated_count``. Hosts outside the top-K
    have ``services_omitted=True`` and render donut-only from
    ``services_summary``. Successive calls within
    ``settings.flow_board_topology_cache_ttl`` reuse the cached result.

    Result rows are scoped to the caller's Livestatus contact groups (admins
    and ``general.see_all`` users see everything). The cache key includes the
    auth-user, so per-tab cache hits never leak rows across users.
    """
    connection = get_connection(connection_id)
    if connection is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Connection not registered"
        )

    limit = (
        services_per_host
        if services_per_host is not None
        else settings.flow_board_max_services_per_host
    )
    top_k = (
        top_affected_hosts
        if top_affected_hosts is not None
        else settings.flow_board_top_affected_hosts
    )
    auth_user = resolve_auth_user(current_user.name, current_user.is_admin)
    cache_key = _TopologyCacheKey(
        connection_id=connection_id,
        root=root,
        child_layers=child_layers,
        parent_layers=parent_layers,
        include_services=include_services,
        services_per_host=limit,
        top_affected_hosts=top_k,
        auth_user=auth_user,
    )
    ttl = settings.flow_board_topology_cache_ttl

    cached = _topology_cache.get(cache_key)
    if cached is not None and time.monotonic() - cached[0] < ttl:
        return cached[1]

    lock = _topology_cache_locks.setdefault(cache_key, asyncio.Lock())
    cached_written = False
    try:
        async with lock:
            # Re-check inside the lock — a concurrent waiter may have populated it.
            cached = _topology_cache.get(cache_key)
            if cached is not None and time.monotonic() - cached[0] < ttl:
                return cached[1]

            async def _build() -> list[TopologyNode]:
                return await build_topology_response(
                    connection,
                    include_services=include_services,
                    services_per_host=limit,
                    top_affected_hosts=top_k,
                    root=root,
                    child_layers=child_layers,
                    parent_layers=parent_layers,
                )

            # auth_user is None outside CMK or for see-all callers, so the
            # contact-group wrap only fires when the connection supports it
            # (LivestatusConnection does, the test backend doesn't).
            if auth_user is not None and hasattr(connection, "with_auth_user"):
                async with connection.with_auth_user(auth_user):
                    result = await _build()
            else:
                result = await _build()

            # Insertion-order eviction (CPython 3.7+ dicts preserve insertion order).
            if len(_topology_cache) >= _TOPOLOGY_CACHE_MAX:
                _drop_topology_cache_key(next(iter(_topology_cache)))
            _topology_cache[cache_key] = (time.monotonic(), result)
            cached_written = True
            return result
    finally:
        # If the query raised (e.g. livestatus timeout), the lock is released
        # by `async with` but the dict entry would otherwise leak.
        if not cached_written:
            _topology_cache_locks.pop(cache_key, None)


@router.get("/{connection_id}/perf-metrics", response_model=list[str])
async def get_perf_metrics(
    connection_id: str,
    host: str = Query(...),
    service: str | None = Query(None),
    _: User = Depends(get_current_user),
) -> list[str]:
    """Return perf_data metric names for a host or service (for metric autocomplete)."""
    connection = get_connection(connection_id)
    if connection is None:
        return []
    try:
        if service:
            state = await connection.get_service_state(host, service)
        else:
            state = await connection.get_host_state(host)
        return _parse_metric_names(state.perf_data)
    except Exception:
        return []


def _parse_metric_names(perf_data: str) -> list[str]:
    return [
        part[: part.index("=")].strip("'")
        for part in re.findall(r"(?:'[^']+'|[^\s]+)=[^\s]*", perf_data)
    ]


class MetricPoint(BaseModel):
    ts: float
    value: float
    unit: str


class GraphGroupResponse(BaseModel):
    id: str
    title: str
    metrics: list[str]


class MetricHistoryResponse(BaseModel):
    series: dict[str, list[MetricPoint]]
    titles: dict[str, str]
    graphs: list[GraphGroupResponse] = []


@router.get("/{connection_id}/metric-history", response_model=MetricHistoryResponse)
async def get_metric_history(
    connection_id: str,
    host: str = Query(...),
    service: str | None = Query(None),
    minutes: int = Query(60, ge=1, le=10080),
    _: User = Depends(get_current_user),
) -> MetricHistoryResponse:
    """Return RRD metric history for a host/service using Livestatus rrddata (Checkmk only)."""
    connection = get_connection(connection_id)
    if connection is None:
        return MetricHistoryResponse(series={}, titles={})
    end = int(time.time())
    start = end - minutes * 60
    try:
        raw = await connection.get_metric_history(host, service, start, end)
    except Exception as exc:
        logger.error("metric-history error: %s", exc, exc_info=True)
        return MetricHistoryResponse(
            series={"_error": [MetricPoint(ts=0, value=0, unit=str(exc))]},
            titles={},
        )
    return MetricHistoryResponse(
        series={
            label: [MetricPoint(ts=ts, value=v, unit=u) for ts, v, u in pts]
            for label, pts in raw.series.items()
        },
        titles=raw.titles,
        graphs=[GraphGroupResponse(id=g.id, title=g.title, metrics=g.metrics) for g in raw.graphs],
    )


class HostGeo(BaseModel):
    lat: float
    lng: float


@router.get("/{connection_id}/host-geo", response_model=HostGeo | None)
async def get_host_geo(
    connection_id: str,
    host: str = Query(...),
    _: User = Depends(get_current_user),
) -> HostGeo | None:
    """Return orbvis_lat/orbvis_lng coordinates for a host, or null if not set."""
    connection = get_connection(connection_id)
    if connection is None:
        return None
    result = await connection.get_host_geo(host)
    return HostGeo(lat=result[0], lng=result[1]) if result else None


@router.get("/{connection_id}/graph-templates", response_model=list[GraphGroupResponse])
async def get_graph_templates_for_object(
    connection_id: str,
    host: str = Query(...),
    service: str | None = Query(None),
    _: User = Depends(get_current_user),
) -> list[GraphGroupResponse]:
    """Return applicable CMK graph template groups for a host/service (for graph object properties)."""
    connection = get_connection(connection_id)
    if connection is None:
        return []
    groups = await connection.get_graph_templates(host, service)
    return [GraphGroupResponse(id=g.id, title=g.title, metrics=g.metrics) for g in groups]


@router.get("/{connection_id}/object-details", response_model=ObjectDetails | None)
async def get_object_details(
    connection_id: str,
    obj_type: str = Query(..., alias="type", regex="^(host|service)$"),
    host: str = Query(...),
    service: str | None = Query(None),
    _: User = Depends(get_current_user),
) -> ObjectDetails | None:
    """Return on-demand drawer/properties details for a host or service.

    Kept off the WebSocket state stream because long_output, comments,
    downtimes and topology can each be many KB and rarely change between
    checks. The Drawer fetches this once on open.
    """
    connection = get_connection(connection_id)
    if connection is None:
        return None
    if obj_type == "host":
        return await connection.get_host_details(host)
    if not service:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="service query parameter required for type=service",
        )
    return await connection.get_service_details(host, service)


@router.get("/{connection_id}/objects", response_model=list[str])
async def list_backend_objects(
    connection_id: str,
    obj_type: str = Query(..., alias="type"),
    host: str | None = Query(None),
    _: User = Depends(require_admin),
) -> list[str]:
    """Return available object names from a connection (for editor autocomplete)."""
    return await get_connection_objects(connection_id, obj_type, host)


@router.get("/{connection_id}/aggregations", response_model=list[AggregationInfo])
async def list_backend_aggregations(
    connection_id: str,
    user: User = Depends(get_current_user),
) -> list[AggregationInfo]:
    """Return all configured Checkmk BI aggregations for editor autocomplete."""
    connection = get_connection(connection_id)
    if connection is None:
        return []
    try:
        # Use the user's auth context so cmk.bi filters by their permissions.
        with_auth = getattr(connection, "with_auth_user", None)
        if with_auth is not None:
            async with with_auth(user.name):
                return await connection.list_aggregations()
        return await connection.list_aggregations()
    except Exception as exc:
        logger.warning("list_aggregations failed for connection %s: %s", connection_id, exc)
        return []
