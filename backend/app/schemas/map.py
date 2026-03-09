"""Map configuration schemas."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class MapObject(BaseModel):
    id: str
    type: Literal["host", "service", "hostgroup", "servicegroup", "map", "shape", "line", "textbox"]
    x: int | float = 0
    y: int | float = 0
    # Geographic coordinates (worldmap)
    lat: float | None = None
    lng: float | None = None
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
    view_type: str = "icon"  # 'icon' | 'text' | 'gadget'
    gadget_type: str | None = None   # 'gauge' | 'bar' | 'trafficlight'
    gadget_metric: str | None = None  # perf metric label, None = first
    icon_size: int | None = None      # per-object override, None = use map default
    label_show: bool = True
    label_text: str | None = None
    # Label styling
    label_x: int = 0
    label_y: int = 0
    label_size: int = 11
    label_color: str = "#ffffff"
    label_background: str = "transparent"
    # Link
    url: str | None = None
    url_target: str = "_blank"
    # Stacking
    z: int = 1
    # Extra properties
    extra: dict[str, Any] = Field(default_factory=dict)


class MapGlobals(BaseModel):
    alias: str = ""
    background_image: str | None = None
    icon_size: int = 22
    backend_id: str = "live_1"
    hover_template: str | None = None
    context_template: str | None = None
    # Map type
    map_type: Literal["static", "worldmap", "automap", "radar"] = "static"
    # Worldmap initial view
    worldmap_lat: float = 51.0
    worldmap_lng: float = 10.0
    worldmap_zoom: int = 5


class MapConfig(BaseModel):
    name: str
    globals: MapGlobals = Field(default_factory=MapGlobals)
    objects: list[MapObject] = Field(default_factory=list)


class MapCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9_\-]+$")
    alias: str = ""
    background_image: str | None = None
    icon_size: int = 22
    backend_id: str = "live_1"
    map_type: Literal["static", "worldmap", "automap", "radar"] = "static"


class MapUpdate(BaseModel):
    alias: str | None = None
    background_image: str | None = None
    icon_size: int | None = None
    backend_id: str | None = None
    map_type: Literal["static", "worldmap", "automap", "radar"] | None = None
    worldmap_lat: float | None = None
    worldmap_lng: float | None = None
    worldmap_zoom: int | None = None


class MapRead(BaseModel):
    name: str
    alias: str
    background_image: str | None
    icon_size: int
    backend_id: str
    map_type: str
    object_count: int
