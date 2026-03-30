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
    notifications_enabled: bool = True
    active_checks_enabled: bool = True
    address: str = ""
    last_check: float | None = None
    state_type: str = ""  # "HARD" | "SOFT" | ""
    current_attempt: int = 0
    max_attempts: int = 0
    last_state_change: float | None = None


class MapStates(BaseModel):
    map_name: str
    states: list[ObjectState]
    generated_at: float  # unix timestamp
    backend_ok: bool = True  # False when the monitoring backend is unreachable
