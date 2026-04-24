"""Backend configuration API."""

from __future__ import annotations

import logging
import re
import time

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.api.v1.deps import get_current_user, require_admin
from app.core.config import settings
from app.integrations import checkmk as cmk_integration
from app.models.user import User
from app.schemas.backend import BackendConfig, BackendCreate, BackendUpdate
from app.services import backend_service
from app.services.state_service import get_backend, get_backend_objects

logger = logging.getLogger(__name__)
router = APIRouter()


class TestResult(BaseModel):
    ok: bool
    message: str


@router.get("", response_model=list[BackendConfig])
async def list_backends(_: User = Depends(require_admin)) -> list[BackendConfig]:
    return backend_service.load_all()


@router.post("", response_model=BackendConfig, status_code=status.HTTP_201_CREATED)
async def create_backend(data: BackendCreate, _: User = Depends(require_admin)) -> BackendConfig:
    # BackendCreate = BackendConfig (type alias), so data can be passed directly.
    try:
        return backend_service.create(data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from None


@router.put("/{backend_id}", response_model=BackendConfig)
async def update_backend(
    backend_id: str,
    data: BackendUpdate,
    _: User = Depends(require_admin),
) -> BackendConfig:
    updated = BackendConfig(id=backend_id, **data.model_dump())
    result = backend_service.update(backend_id, updated)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Backend not found")
    return result


@router.delete("/{backend_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_backend(backend_id: str, _: User = Depends(require_admin)) -> None:
    if not backend_service.delete(backend_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Backend not found")


class BackendContext(BaseModel):
    monitoring_core: str | None  # 'cmc', 'nagios', or None
    omd_site: str | None


@router.get("/{backend_id}/context", response_model=BackendContext)
async def get_backend_context(backend_id: str, _: User = Depends(require_admin)) -> BackendContext:
    """Return OMD/CMC context for the connection settings UI.

    Only meaningful for Livestatus backends inside an OMD site. Returns nulls
    for non-OMD setups. The backend_id is accepted for future multi-site use;
    currently core detection is always local.
    """
    return BackendContext(
        monitoring_core=cmk_integration.get_monitoring_core(),
        omd_site=settings.checkmk_site or None,
    )


@router.get("/{backend_id}/test", response_model=TestResult)
async def test_backend(backend_id: str, _: User = Depends(require_admin)) -> TestResult:
    """Test connectivity of a saved backend."""
    backend = get_backend(backend_id)
    if backend is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Backend not registered (restart needed?)"
        )
    try:
        ok = await backend.is_available()
        return TestResult(ok=ok, message="Connection successful" if ok else "Backend not reachable")
    except Exception as exc:
        return TestResult(ok=False, message=str(exc))


@router.post("/test-connection", response_model=TestResult)
async def test_connection(data: BackendCreate, _: User = Depends(require_admin)) -> TestResult:
    """Test connection details without saving – used by the create/edit dialog."""
    try:
        backend = backend_service.build_instance(data)
        ok = await backend.is_available()
        return TestResult(ok=ok, message="Connection successful" if ok else "Backend not reachable")
    except Exception as exc:
        return TestResult(ok=False, message=str(exc))


class ServiceNode(BaseModel):
    name: str
    state: str
    output: str


class TopologyNode(BaseModel):
    name: str
    parents: list[str]
    state: str
    output: str
    services: list[ServiceNode] = []


@router.get("/{backend_id}/topology", response_model=list[TopologyNode])
async def get_topology(
    backend_id: str,
    include_services: bool = Query(False),
    _: User = Depends(get_current_user),
) -> list[TopologyNode]:
    """Return host topology for flow board rendering."""
    backend = get_backend(backend_id)
    if backend is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Backend not registered")
    nodes = await backend.get_topology()
    if include_services:
        result: list[TopologyNode] = []
        for node in nodes:
            svcs = await backend.get_host_services(node["name"])
            result.append(TopologyNode(**node, services=[ServiceNode(**s) for s in svcs]))
        return result
    return [TopologyNode(**n) for n in nodes]


@router.get("/{backend_id}/perf-metrics", response_model=list[str])
async def get_perf_metrics(
    backend_id: str,
    host: str = Query(...),
    service: str | None = Query(None),
    _: User = Depends(get_current_user),
) -> list[str]:
    """Return perf_data metric names for a host or service (for metric autocomplete)."""
    backend = get_backend(backend_id)
    if backend is None:
        return []
    try:
        if service:
            state = await backend.get_service_state(host, service)
        else:
            state = await backend.get_host_state(host)
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


@router.get("/{backend_id}/metric-history", response_model=MetricHistoryResponse)
async def get_metric_history(
    backend_id: str,
    host: str = Query(...),
    service: str | None = Query(None),
    minutes: int = Query(60, ge=1, le=10080),
    _: User = Depends(get_current_user),
) -> MetricHistoryResponse:
    """Return RRD metric history for a host/service using Livestatus rrddata (Checkmk only)."""
    backend = get_backend(backend_id)
    if backend is None:
        return MetricHistoryResponse(series={}, titles={})
    end = int(time.time())
    start = end - minutes * 60
    try:
        raw = await backend.get_metric_history(host, service, start, end)
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


@router.get("/{backend_id}/host-geo", response_model=HostGeo | None)
async def get_host_geo(
    backend_id: str,
    host: str = Query(...),
    _: User = Depends(get_current_user),
) -> HostGeo | None:
    """Return orbvis_lat/orbvis_lng coordinates for a host, or null if not set."""
    backend = get_backend(backend_id)
    if backend is None:
        return None
    result = await backend.get_host_geo(host)
    return HostGeo(lat=result[0], lng=result[1]) if result else None


@router.get("/{backend_id}/graph-templates", response_model=list[GraphGroupResponse])
async def get_graph_templates_for_object(
    backend_id: str,
    host: str = Query(...),
    service: str | None = Query(None),
    _: User = Depends(get_current_user),
) -> list[GraphGroupResponse]:
    """Return applicable CMK graph template groups for a host/service (for graph object properties)."""
    backend = get_backend(backend_id)
    if backend is None:
        return []
    groups = await backend.get_graph_templates(host, service)
    return [GraphGroupResponse(id=g.id, title=g.title, metrics=g.metrics) for g in groups]


@router.get("/{backend_id}/objects", response_model=list[str])
async def list_backend_objects(
    backend_id: str,
    obj_type: str = Query(..., alias="type"),
    host: str | None = Query(None),
    _: User = Depends(require_admin),
) -> list[str]:
    """Return available object names from a backend (for editor autocomplete)."""
    return await get_backend_objects(backend_id, obj_type, host)
