"""Monitoring state schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

HostStateValue = Literal["UP", "DOWN", "UNREACHABLE", "PENDING"]
ServiceStateValue = Literal["OK", "WARNING", "CRITICAL", "UNKNOWN", "PENDING"]


class ObjectState(BaseModel):
    object_id: str
    type: str
    state: str
    output: str = ""
    perf_data: str = ""
    acknowledged: bool = False
    in_downtime: bool = False
    stale: bool = False


class MapStates(BaseModel):
    map_name: str
    states: list[ObjectState]
    generated_at: float  # unix timestamp
    backend_ok: bool = True  # False when the monitoring backend is unreachable
