#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Metric computation endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from cmk.orbvis_backend.api.v1.deps import get_current_user
from cmk.orbvis_backend.connections.livestatus import LivestatusConnection
from cmk.orbvis_backend.models.user import User
from cmk.orbvis_backend.services import state_service
from cmk.orbvis_backend.services.perfometer_service import (
    PerfometerResult,
    compute_perfometer,
    metric_unit_formats,
)

router = APIRouter()


class MetricUnitPrecisionOut(BaseModel):
    type: str  # "auto" | "strict"
    digits: int


class MetricUnitOut(BaseModel):
    """cmk-shared-typing UnitFormat plus the perfdata→registry scale factor."""

    notation: str  # decimal|si|iec|standard_scientific|engineering_scientific|time
    symbol: str
    precision: MetricUnitPrecisionOut
    scale: float


class PerfometerSegmentOut(BaseModel):
    pct: float
    color: str


class PerfometerResultOut(BaseModel):
    label: str
    rows: list[list[PerfometerSegmentOut]]
    pcts: list[float]


@router.get("/metrics/perfometer", response_model=PerfometerResultOut | None)
async def get_perfometer(
    connection_id: str,
    host: str,
    service: str,
    _current_user: User = Depends(get_current_user),
) -> PerfometerResultOut | None:
    connection = state_service.get_connection(connection_id)
    if connection is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection not found",
        )
    # Non-Livestatus backends (TestBackend, Icinga2) cannot supply perf-data
    # in the form the perfometer compiler expects. Returning null keeps the
    # gadget rendering quiet — the gauge falls back to its raw value, and
    # the console doesn't fill with 404s on every demo map.
    if not isinstance(connection, LivestatusConnection):
        return None

    perf_data, check_command = await connection.get_service_perf_and_cmd(host, service)
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
        pcts=result.pcts,
    )


@router.get("/metrics/units", response_model=dict[str, MetricUnitOut])
async def get_metric_units(
    connection_id: str,
    host: str,
    service: str,
    _current_user: User = Depends(get_current_user),
) -> dict[str, MetricUnitOut]:
    """Display units for a service's perfdata metrics, straight from the CMK
    metric registry — so clients render values exactly like the Checkmk GUI
    (IEC for memory, SI for bandwidth, auto-scaled time, …). Keys are the raw
    perfdata labels; metrics without a registry entry are omitted and fall
    back to client-side heuristics."""
    connection = state_service.get_connection(connection_id)
    if connection is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection not found",
        )
    if not isinstance(connection, LivestatusConnection):
        return {}

    perf_data, check_command = await connection.get_service_perf_and_cmd(host, service)
    if not perf_data:
        return {}

    return {
        label: MetricUnitOut(
            notation=fmt.notation,
            symbol=fmt.symbol,
            precision=MetricUnitPrecisionOut(type=fmt.precision_type, digits=fmt.precision_digits),
            scale=fmt.scale,
        )
        for label, fmt in metric_unit_formats(perf_data, check_command).items()
    }
