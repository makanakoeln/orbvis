"""Map configuration schemas."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class MapObject(BaseModel):
    id: str
    type: Literal["host", "service", "hostgroup", "servicegroup", "map", "shape", "line", "textbox"]
    x: int | float
    y: int | float
    # Host/Service specific
    host_name: str | None = None
    service_description: str | None = None
    # Group specific
    group_name: str | None = None
    # Map object
    map_name: str | None = None
    # Shape/icon
    icon: str | None = None
    # Line
    line_type: int | None = None
    view_type: str = "icon"
    label_show: bool = True
    label_text: str | None = None
    # Extra properties
    extra: dict[str, Any] = Field(default_factory=dict)


class MapGlobals(BaseModel):
    alias: str = ""
    background_image: str | None = None
    icon_size: int = 22
    backend_id: str = "live_1"
    hover_template: str | None = None
    context_template: str | None = None


class MapConfig(BaseModel):
    name: str
    globals: MapGlobals = Field(default_factory=MapGlobals)
    objects: list[MapObject] = Field(default_factory=list)


class MapCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    alias: str = ""
    background_image: str | None = None
    icon_size: int = 22
    backend_id: str = "live_1"


class MapUpdate(BaseModel):
    alias: str | None = None
    background_image: str | None = None
    icon_size: int | None = None
    backend_id: str | None = None


class MapRead(BaseModel):
    name: str
    alias: str
    background_image: str | None
    icon_size: int
    backend_id: str
    object_count: int
