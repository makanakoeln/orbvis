"""Connection configuration API."""

from __future__ import annotations

import asyncio
import logging
import re
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator

from app.api.v1.deps import (
    can_run_command,
    get_current_user,
    require_configure,
    require_connection_read,
    resolve_auth_user,
)
from app.connections.base import ConnectionBase, ServiceRow, TopologyRow, topology_problem_rank
from app.core.config import settings
from app.form_specs import FORM_SPECS_AVAILABLE
from app.integrations import checkmk as cmk_integration

if FORM_SPECS_AVAILABLE:
    from app.form_specs import serialize_form_spec
    from app.form_specs._wire_types import AnyWireFormSpec
    from app.form_specs.connections import (
        config_to_form_data,
        connection_spec,
        form_data_to_config,
    )
from app.models.user import User
from app.schemas.board import AggregationInfo, AggregationNode, normalize_object_filter
from app.schemas.connection import (
    REDACTED_SECRET,
    ConnectionConfig,
    ConnectionCreate,
    ConnectionUpdate,
    _redact,
)
from app.schemas.state import ObjectDetails, ServicesSummary
from app.services import connection_service
from app.services.state_service import (
    get_connection,
    get_connection_objects,
    list_connection_folders,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@asynccontextmanager
async def _auth_scope(connection: ConnectionBase, user: User) -> AsyncIterator[None]:
    """Scope livestatus queries inside the block to the user's contact visibility.

    ``resolve_auth_user`` returns ``None`` for admins / users with
    ``general.see_all`` — those run UNSCOPED. Livestatus ``AuthUser`` only
    knows contacts, and cmkadmin typically is no contact, so passing the raw
    username would silently filter every query down to zero rows.
    """
    auth_user = resolve_auth_user(user.name, user.is_admin)
    with_auth = getattr(connection, "with_auth_user", None)
    if auth_user is not None and with_auth is not None:
        async with with_auth(auth_user):
            yield
    else:
        yield


class TestResult(BaseModel):
    ok: bool
    message: str


@router.get("", response_model=list[ConnectionConfig])
async def list_backends(_: User = Depends(require_connection_read)) -> list[ConnectionConfig]:
    return [_redact(b) for b in connection_service.load_all()]


if FORM_SPECS_AVAILABLE:

    class FormCreateBody(BaseModel):
        # ID lands on disk as a filename and in URLs — restrict to a safe charset.
        # Path-traversal via ``id="../foo"`` would otherwise let an admin overwrite
        # neighbouring connection JSONs (admin-only endpoint, but defense in depth).
        id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
        form: dict[str, object]

    @router.get("/schema")
    async def get_connection_schema(_: User = Depends(require_configure)) -> AnyWireFormSpec:
        return serialize_form_spec(connection_spec(cmk_integration.get_monitoring_core()))

    @router.get("/{connection_id}/form")
    async def get_connection_form_data(
        connection_id: str, _: User = Depends(require_configure)
    ) -> dict[str, object]:
        existing = next((b for b in connection_service.load_all() if b.id == connection_id), None)
        if existing is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Connection not found"
            )
        return config_to_form_data(_redact(existing))

    @router.post("/form", response_model=ConnectionConfig, status_code=status.HTTP_201_CREATED)
    async def create_connection_from_form(
        body: FormCreateBody, _: User = Depends(require_configure)
    ) -> ConnectionConfig:
        try:
            created = form_data_to_config(body.form, existing=None, connection_id=body.id)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from None
        try:
            result = connection_service.create(created)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from None
        return _redact(result)

    @router.post("/form/test-connection", response_model=TestResult)
    async def test_connection_from_form(
        body: FormCreateBody, _: User = Depends(require_configure)
    ) -> TestResult:
        """Test FormSpec connection data without saving — used by the edit dialog."""
        try:
            cfg = form_data_to_config(body.form, existing=None, connection_id=body.id)
        except ValueError as exc:
            return TestResult(ok=False, message=str(exc))
        try:
            connection = connection_service.build_instance(cfg)
            ok = await connection.is_available()
            return TestResult(
                ok=ok, message="Connection successful" if ok else "Connection not reachable"
            )
        except Exception as exc:
            return TestResult(ok=False, message=str(exc))

    @router.put("/{connection_id}/form", response_model=ConnectionConfig)
    async def update_connection_from_form(
        connection_id: str,
        form_data: dict[str, object],
        _: User = Depends(require_configure),
    ) -> ConnectionConfig:
        existing = next((b for b in connection_service.load_all() if b.id == connection_id), None)
        if existing is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Connection not found"
            )
        try:
            updated = form_data_to_config(form_data, existing=existing, connection_id=connection_id)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from None
        result = connection_service.update(connection_id, updated)
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Connection not found"
            )
        _invalidate_topology_cache(connection_id)
        return _redact(result)


@router.post("", response_model=ConnectionConfig, status_code=status.HTTP_201_CREATED)
async def create_backend(
    data: ConnectionCreate, _: User = Depends(require_configure)
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
    _: User = Depends(require_configure),
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
async def delete_backend(connection_id: str, _: User = Depends(require_configure)) -> None:
    if not connection_service.delete(connection_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connection not found")
    _invalidate_topology_cache(connection_id)


class ConnectionContext(BaseModel):
    monitoring_core: str | None  # 'cmc', 'nagios', or None
    omd_site: str | None


@router.get("/{connection_id}/context", response_model=ConnectionContext)
async def get_backend_context(
    connection_id: str, _: User = Depends(require_configure)
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
async def test_backend(connection_id: str, _: User = Depends(require_configure)) -> TestResult:
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
async def test_connection(
    data: ConnectionCreate, _: User = Depends(require_configure)
) -> TestResult:
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
    user: User = Depends(get_current_user),
) -> list[str]:
    """Return perf_data metric names for a host or service (for metric autocomplete)."""
    connection = get_connection(connection_id)
    if connection is None:
        return []
    try:
        async with _auth_scope(connection, user):
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
    user: User = Depends(get_current_user),
) -> MetricHistoryResponse:
    """Return RRD metric history for a host/service using Livestatus rrddata (Checkmk only)."""
    connection = get_connection(connection_id)
    if connection is None:
        return MetricHistoryResponse(series={}, titles={})
    end = int(time.time())
    start = end - minutes * 60
    try:
        async with _auth_scope(connection, user):
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
    user: User = Depends(get_current_user),
) -> HostGeo | None:
    """Return orbvis_lat/orbvis_lng coordinates for a host, or null if not set."""
    connection = get_connection(connection_id)
    if connection is None:
        return None
    async with _auth_scope(connection, user):
        result = await connection.get_host_geo(host)
    return HostGeo(lat=result[0], lng=result[1]) if result else None


@router.get("/{connection_id}/graph-templates", response_model=list[GraphGroupResponse])
async def get_graph_templates_for_object(
    connection_id: str,
    host: str = Query(...),
    service: str | None = Query(None),
    user: User = Depends(get_current_user),
) -> list[GraphGroupResponse]:
    """Return applicable CMK graph template groups for a host/service (for graph object properties)."""
    connection = get_connection(connection_id)
    if connection is None:
        return []
    async with _auth_scope(connection, user):
        groups = await connection.get_graph_templates(host, service)
    return [GraphGroupResponse(id=g.id, title=g.title, metrics=g.metrics) for g in groups]


@router.get("/{connection_id}/object-details", response_model=ObjectDetails | None)
async def get_object_details(
    connection_id: str,
    obj_type: str = Query(..., alias="type", pattern="^(host|service)$"),
    host: str = Query(...),
    service: str | None = Query(None),
    user: User = Depends(get_current_user),
) -> ObjectDetails | None:
    """Return on-demand drawer/properties details for a host or service.

    Kept off the WebSocket state stream because long_output, comments,
    downtimes and topology can each be many KB and rarely change between
    checks. The Drawer fetches this once on open.
    """
    connection = get_connection(connection_id)
    if connection is None:
        return None
    async with _auth_scope(connection, user):
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
    search: str | None = Query(None),
    user: User = Depends(get_current_user),
) -> list[str]:
    """Return available object names from a connection (for editor autocomplete).

    ``search`` is a case-insensitive substring applied server-side so the editor
    can fetch-on-type (CMK autocompleter style) instead of pulling every name.
    Non-admin editors are scoped to their Checkmk contact groups so they only see
    hosts they monitor.
    """
    auth_user = resolve_auth_user(user.name, user.is_admin)
    return await get_connection_objects(connection_id, obj_type, host, search, auth_user=auth_user)


class FolderOption(BaseModel):
    """One SETUP folder for the foldertree root-folder picker."""

    path: str
    title: str


@router.get("/{connection_id}/folders", response_model=list[FolderOption])
async def list_backend_folders(
    connection_id: str,
    _: User = Depends(require_configure),
) -> list[dict[str, str]]:
    """Return the connection's SETUP folders (for the foldertree root picker).

    Stays configure-gated: the raw SETUP folder skeleton is not scoped by
    ``with_auth_user`` (that filters host rows, not folder names), so exposing it
    to non-configure users would disclose folder names outside their access.
    """
    return await list_connection_folders(connection_id)


class SiteOption(BaseModel):
    """One monitoring site for the foldertree site-scope picker."""

    id: str
    alias: str


@router.get("/{connection_id}/sites", response_model=list[SiteOption])
async def list_backend_sites(
    connection_id: str,
    _: User = Depends(require_configure),
) -> list[dict[str, str]]:
    """Return the connection's monitoring sites (for the foldertree site picker).

    Empty for single-socket connections, which have no meaningful site choice.
    """
    connection = get_connection(connection_id)
    if connection is None:
        return []
    return await connection.get_sites()


class GroupMember(BaseModel):
    """One row of the host- or service-group triage list shown in the drawer."""

    host: str
    service: str = ""
    state: str
    output: str = ""
    acknowledged: bool = False
    in_downtime: bool = False
    notifications_enabled: bool = True
    last_state_change: float | None = None


@router.get(
    "/{connection_id}/groups/{group_type}/{group_name}/members",
    response_model=list[GroupMember],
)
async def list_group_members(
    connection_id: str,
    group_type: Literal["hostgroup", "servicegroup"],
    group_name: str,
    user: User = Depends(get_current_user),
) -> list[GroupMember]:
    """Return per-member state for a host- or service-group.

    Drives the Members tab of the slide-in drawer. Auth-scoped via Livestatus
    when the connection supports it so users only see members they're
    authorised for.
    """
    connection = get_connection(connection_id)
    if connection is None:
        return []
    async with _auth_scope(connection, user):
        rows = await connection.get_group_member_states(group_type, group_name)
    return [GroupMember.model_validate(dict(r)) for r in rows]


class DyngroupMembersRequest(BaseModel):
    object_types: Literal["host", "service"] = "host"
    object_filter: str

    @field_validator("object_filter")
    @classmethod
    def _validate_filter(cls, v: str) -> str:
        return normalize_object_filter(v)


@router.post(
    "/{connection_id}/dyngroup-members",
    response_model=list[GroupMember],
)
async def list_dyngroup_members(
    connection_id: str,
    body: DyngroupMembersRequest,
    user: User = Depends(get_current_user),
) -> list[GroupMember]:
    """Return per-member state for a dyngroup filter (Members tab in drawer)."""
    connection = get_connection(connection_id)
    if connection is None:
        return []
    async with _auth_scope(connection, user):
        rows = await connection.get_dyngroup_member_states(body.object_types, body.object_filter)
    return [GroupMember.model_validate(dict(r)) for r in rows]


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
        # _auth_scope, not raw user.name: a raw name would scope every BI
        # query to zero hosts for non-contact admins (empty branch compile,
        # "no aggregations" for the people most likely to configure boards).
        async with _auth_scope(connection, user):
            return await connection.list_aggregations()
    except Exception as exc:
        logger.warning("list_aggregations failed for connection %s: %s", connection_id, exc)
        return []


class AggregationTreeResult(BaseModel):
    """Tree-fetch response with a connection-health discriminator.

    Returning a bare ``tree | null`` made it impossible for the EditPanel
    to distinguish "aggregation has zero leaves" from "the connection is
    dead and we couldn't compute a tree". This wrapper lets the UI render
    a "connection unavailable" hint in the latter case.
    """

    tree: AggregationNode | None
    connection_ok: bool


@router.get(
    "/{connection_id}/aggregations/{aggregation_id}/tree",
    response_model=AggregationTreeResult,
)
async def get_backend_aggregation_tree(
    connection_id: str,
    aggregation_id: str,
    depth: int = Query(2, ge=0, le=10),
    user: User = Depends(get_current_user),
) -> AggregationTreeResult:
    """Return the live BI aggregation tree for the editor preview pane.

    Used by the EditPanel to render a "what does this look like right now"
    sample so the designer picking ``expand_depth`` can see the resulting
    fan-out before saving the board. Capped at 10 levels — even a single
    rendering of 200+ leaves makes the EditPanel sluggish.

    Carries a ``connection_ok`` flag so the UI can distinguish "0 leaves"
    from "couldn't reach Checkmk" — the previous bare-tree shape couldn't
    differentiate, so the EditPanel hid the preview in both cases and the
    designer was left guessing.
    """
    connection = get_connection(connection_id)
    if connection is None:
        return AggregationTreeResult(tree=None, connection_ok=False)
    try:
        async with _auth_scope(connection, user):
            tree = await connection.get_aggregation_tree(aggregation_id, depth)
        # Probe connection health independently — a tree of None on a
        # healthy connection is a legitimate "0 leaves" / "aggregation
        # not registered" outcome, not a fetch failure.
        connection_ok = await connection.is_available()
        return AggregationTreeResult(tree=tree, connection_ok=connection_ok)
    except Exception as exc:
        logger.warning(
            "get_aggregation_tree(%s, %s) failed: %s", connection_id, aggregation_id, exc
        )
        return AggregationTreeResult(tree=None, connection_ok=False)


# ---------------------------------------------------------------------------
# Operational commands (ack-removal, force-check, notifications, active-checks)
# ---------------------------------------------------------------------------
# All command verbs route through the livestatus pipe — bypasses CMK REST
# (no automation credentials needed) and works on Nagios + CMC. Note: the pipe
# also bypasses CMK contact-group ACLs; the per-verb command permission
# (can_run_command) is the only gate on the action itself.
_SIMPLE_HOST_COMMANDS: dict[str, str] = {
    "force_check": "SCHEDULE_FORCED_HOST_CHECK;{host};{ts}",
    "enable_notifications": "ENABLE_HOST_NOTIFICATIONS;{host}",
    "disable_notifications": "DISABLE_HOST_NOTIFICATIONS;{host}",
    "enable_checks": "ENABLE_HOST_CHECK;{host}",
    "disable_checks": "DISABLE_HOST_CHECK;{host}",
    "remove_acknowledgement": "REMOVE_HOST_ACKNOWLEDGEMENT;{host}",
}
_SIMPLE_SERVICE_COMMANDS: dict[str, str] = {
    "force_check": "SCHEDULE_FORCED_SVC_CHECK;{host};{svc};{ts}",
    "enable_notifications": "ENABLE_SVC_NOTIFICATIONS;{host};{svc}",
    "disable_notifications": "DISABLE_SVC_NOTIFICATIONS;{host};{svc}",
    "enable_checks": "ENABLE_SVC_CHECK;{host};{svc}",
    "disable_checks": "DISABLE_SVC_CHECK;{host};{svc}",
    "remove_acknowledgement": "REMOVE_SVC_ACKNOWLEDGEMENT;{host};{svc}",
}
_PARAMETERISED_HOST_ACTIONS = {"acknowledge", "add_comment", "schedule_downtime"}
_PARAMETERISED_SERVICE_ACTIONS = {"acknowledge", "add_comment", "schedule_downtime"}


def _cmd_safe(value: str) -> str:
    # Strip field/line separators so user-supplied text can't forge extra fields.
    return value.replace(";", " ").replace("\n", " ").replace("\r", " ")


def _reject_command_separators(value: str) -> str:
    # Host/service names that reach the livestatus command pipe must not carry
    # field (;) or line (\n, \r) separators — a Checkmk object name never does,
    # and allowing them lets a crafted name inject a second COMMAND line.
    if any(sep in value for sep in (";", "\n", "\r")):
        raise ValueError("name must not contain ';', newline or carriage return")
    return value


class HostActionRequest(BaseModel):
    action: str
    host_name: str
    site_id: str | None = None
    comment: str | None = None
    sticky: bool = True
    notify: bool = True
    persistent: bool = False
    start_time: int | None = None
    end_time: int | None = None

    @field_validator("host_name")
    @classmethod
    def _validate_host_name(cls, value: str) -> str:
        return _reject_command_separators(value)


class ServiceActionRequest(BaseModel):
    action: str
    host_name: str
    service_description: str
    site_id: str | None = None
    comment: str | None = None
    sticky: bool = True
    notify: bool = True
    persistent: bool = False
    start_time: int | None = None
    end_time: int | None = None

    @field_validator("host_name", "service_description")
    @classmethod
    def _validate_names(cls, value: str) -> str:
        return _reject_command_separators(value)


def _build_host_command(body: HostActionRequest, user: User) -> str:
    host = _cmd_safe(body.host_name)
    template = _SIMPLE_HOST_COMMANDS.get(body.action)
    if template is not None:
        return template.format(host=host, ts=int(time.time()))
    if body.action not in _PARAMETERISED_HOST_ACTIONS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unknown host action {body.action!r} "
                f"(valid: {sorted(set(_SIMPLE_HOST_COMMANDS) | _PARAMETERISED_HOST_ACTIONS)})"
            ),
        )
    if not body.comment:
        raise HTTPException(status_code=400, detail=f"{body.action} requires a comment")
    author = _cmd_safe(user.name)
    comment = _cmd_safe(body.comment)
    if body.action == "acknowledge":
        return (
            f"ACKNOWLEDGE_HOST_PROBLEM;{host};{int(body.sticky)};{int(body.notify)};"
            f"{int(body.persistent)};{author};{comment}"
        )
    if body.action == "add_comment":
        return f"ADD_HOST_COMMENT;{host};{int(body.persistent)};{author};{comment}"
    if body.action == "schedule_downtime":
        if body.start_time is None or body.end_time is None:
            raise HTTPException(
                status_code=400,
                detail="schedule_downtime requires start_time and end_time",
            )
        return (
            f"SCHEDULE_HOST_DOWNTIME;{host};{body.start_time};{body.end_time};1;0;0;"
            f"{author};{comment}"
        )
    raise HTTPException(status_code=400, detail=f"Unhandled host action {body.action!r}")


def _build_service_command(body: ServiceActionRequest, user: User) -> str:
    host = _cmd_safe(body.host_name)
    svc = _cmd_safe(body.service_description)
    template = _SIMPLE_SERVICE_COMMANDS.get(body.action)
    if template is not None:
        return template.format(host=host, svc=svc, ts=int(time.time()))
    if body.action not in _PARAMETERISED_SERVICE_ACTIONS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unknown service action {body.action!r} "
                f"(valid: {sorted(set(_SIMPLE_SERVICE_COMMANDS) | _PARAMETERISED_SERVICE_ACTIONS)})"
            ),
        )
    if not body.comment:
        raise HTTPException(status_code=400, detail=f"{body.action} requires a comment")
    author = _cmd_safe(user.name)
    comment = _cmd_safe(body.comment)
    if body.action == "acknowledge":
        return (
            f"ACKNOWLEDGE_SVC_PROBLEM;{host};{svc};{int(body.sticky)};{int(body.notify)};"
            f"{int(body.persistent)};{author};{comment}"
        )
    if body.action == "add_comment":
        return f"ADD_SVC_COMMENT;{host};{svc};{int(body.persistent)};{author};{comment}"
    if body.action == "schedule_downtime":
        if body.start_time is None or body.end_time is None:
            raise HTTPException(
                status_code=400,
                detail="schedule_downtime requires start_time and end_time",
            )
        return (
            f"SCHEDULE_SVC_DOWNTIME;{host};{svc};{body.start_time};{body.end_time};1;0;0;"
            f"{author};{comment}"
        )
    raise HTTPException(status_code=400, detail=f"Unhandled service action {body.action!r}")


def _require_command_permission(user: User, action: str) -> None:
    if not can_run_command(user, action):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Missing Checkmk permission for action {action!r}",
        )


@router.post("/{connection_id}/host-action", status_code=status.HTTP_204_NO_CONTENT)
async def host_action(
    connection_id: str,
    body: HostActionRequest,
    user: User = Depends(get_current_user),
) -> None:
    _require_command_permission(user, body.action)
    cmd = _build_host_command(body, user)
    connection = get_connection(connection_id)
    if connection is None or not hasattr(connection, "send_command"):
        raise HTTPException(status_code=404, detail="Connection not found or not livestatus-backed")
    try:
        await connection.send_command(cmd, body.site_id)
    except Exception as exc:
        logger.warning("host_action %s on %s failed: %s", body.action, body.host_name, exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/{connection_id}/service-action", status_code=status.HTTP_204_NO_CONTENT)
async def service_action(
    connection_id: str,
    body: ServiceActionRequest,
    user: User = Depends(get_current_user),
) -> None:
    _require_command_permission(user, body.action)
    cmd = _build_service_command(body, user)
    connection = get_connection(connection_id)
    if connection is None or not hasattr(connection, "send_command"):
        raise HTTPException(status_code=404, detail="Connection not found or not livestatus-backed")
    try:
        await connection.send_command(cmd, body.site_id)
    except Exception as exc:
        logger.warning(
            "service_action %s on %s/%s failed: %s",
            body.action,
            body.host_name,
            body.service_description,
            exc,
        )
        raise HTTPException(status_code=502, detail=str(exc)) from exc
