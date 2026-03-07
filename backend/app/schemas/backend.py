"""Pydantic schemas for monitoring backend configuration."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class BackendConfig(BaseModel):
    id: str
    type: Literal["livestatus", "test"] = "livestatus"
    label: str = ""
    # Livestatus connection (Unix socket OR TCP, not both)
    socket_path: str | None = None
    host: str | None = None
    port: int = 6557
    timeout: float = 10.0
    checkmk_url: str | None = None  # e.g. http://localhost/heute


BackendCreate = BackendConfig


class BackendUpdate(BaseModel):
    """Full replacement of all mutable fields (id stays fixed)."""
    type: Literal["livestatus", "test"] = "livestatus"
    label: str = ""
    socket_path: str | None = None
    host: str | None = None
    port: int = 6557
    timeout: float = 10.0
    checkmk_url: str | None = None
