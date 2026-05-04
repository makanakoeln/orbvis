"""Metric computation endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.api.v1.deps import get_current_user
from app.backends.livestatus import LivestatusBackend
from app.models.user import User
from app.services import state_service
from app.services.perfometer_service import PerfometerResult, compute_perfometer

router = APIRouter()


class PerfometerSegmentOut(BaseModel):
    pct: float
    color: str


class PerfometerResultOut(BaseModel):
    label: str
    rows: list[list[PerfometerSegmentOut]]


@router.get("/metrics/perfometer", response_model=PerfometerResultOut | None)
async def get_perfometer(
    backend_id: str,
    host: str,
    service: str,
    _current_user: User = Depends(get_current_user),
) -> PerfometerResultOut | None:
    backend = state_service.get_backend(backend_id)
    if not isinstance(backend, LivestatusBackend):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Backend not found or not a Livestatus backend",
        )

    perf_data, check_command = await backend.get_service_perf_and_cmd(host, service)
    if not perf_data:
        return None

    result: PerfometerResult | None = compute_perfometer(perf_data, check_command)
    if result is None:
        return None

    return PerfometerResultOut(
        label=result.label,
        rows=[
            [PerfometerSegmentOut(pct=seg.pct, color=seg.color) for seg in row]
            for row in result.rows
        ],
    )
