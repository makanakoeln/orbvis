"""Backend configuration API."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.api.v1.deps import get_current_user, require_admin
from app.schemas.backend import BackendConfig, BackendCreate, BackendUpdate
from app.services import backend_service
from app.services.state_service import get_backend, get_backend_objects

router = APIRouter()


class TestResult(BaseModel):
    ok: bool
    message: str


@router.get("", response_model=list[BackendConfig])
async def list_backends(_: object = Depends(require_admin)):
    return backend_service.load_all()


@router.post("", response_model=BackendConfig, status_code=201)
async def create_backend(data: BackendCreate, _: object = Depends(require_admin)):
    # BackendCreate = BackendConfig (type alias), so data can be passed directly.
    try:
        return backend_service.create(data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.put("/{backend_id}", response_model=BackendConfig)
async def update_backend(
    backend_id: str,
    data: BackendUpdate,
    _: object = Depends(require_admin),
):
    updated = BackendConfig(id=backend_id, **data.model_dump())
    result = backend_service.update(backend_id, updated)
    if result is None:
        raise HTTPException(status_code=404, detail="Backend not found")
    return result


@router.delete("/{backend_id}", status_code=204)
async def delete_backend(backend_id: str, _: object = Depends(require_admin)):
    if not backend_service.delete(backend_id):
        raise HTTPException(status_code=404, detail="Backend not found")


@router.get("/{backend_id}/test", response_model=TestResult)
async def test_backend(backend_id: str, _: object = Depends(require_admin)):
    """Test connectivity of a saved backend."""
    backend = get_backend(backend_id)
    if backend is None:
        raise HTTPException(status_code=404, detail="Backend not registered (restart needed?)")
    try:
        ok = await backend.is_available()
        return TestResult(ok=ok, message="Connection successful" if ok else "Backend not reachable")
    except Exception as exc:
        return TestResult(ok=False, message=str(exc))


@router.post("/test-connection", response_model=TestResult)
async def test_connection(data: BackendCreate, _: object = Depends(require_admin)):
    """Test connection details without saving – used by the create/edit dialog."""
    try:
        backend = backend_service.build_instance(data)
        ok = await backend.is_available()
        return TestResult(ok=ok, message="Connection successful" if ok else "Backend not reachable")
    except Exception as exc:
        return TestResult(ok=False, message=str(exc))


class TopologyNode(BaseModel):
    name: str
    parents: list[str]
    state: str
    output: str


@router.get("/{backend_id}/topology", response_model=list[TopologyNode])
async def get_topology(backend_id: str, _: object = Depends(get_current_user)):
    """Return host topology for automap rendering."""
    backend = get_backend(backend_id)
    if backend is None:
        raise HTTPException(status_code=404, detail="Backend not registered")
    return await backend.get_topology()


@router.get("/{backend_id}/perf-metrics", response_model=list[str])
async def get_perf_metrics(
    backend_id: str,
    host: str = Query(...),
    service: str | None = Query(None),
    _: object = Depends(get_current_user),
):
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
    import re
    names = []
    for part in re.findall(r"(?:'[^']+'|[^\s]+)=[^\s]*", perf_data):
        eq = part.index("=")
        names.append(part[:eq].strip("'"))
    return names


@router.get("/{backend_id}/objects", response_model=list[str])
async def list_backend_objects(
    backend_id: str,
    obj_type: str = Query(..., alias="type"),
    host: str | None = Query(None),
    _: object = Depends(require_admin),
):
    """Return available object names from a backend (for editor autocomplete)."""
    return await get_backend_objects(backend_id, obj_type, host)
