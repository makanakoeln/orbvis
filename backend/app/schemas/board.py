"""Board configuration schemas."""

from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field

ObjectType = Literal[
    "host", "service", "hostgroup", "servicegroup",
    "map", "image", "line", "textbox", "cmk_label",
]

LineStyle = Literal["plain", "arrow_end", "arrow_start", "arrow_both", "dashed", "weathermap"]


class LabelConfig(BaseModel):
    show: bool = True
    text: str | None = None
    x: int = 0
    y: int = 0
    size: int = 11
    color: str = "#ffffff"
    background: str = "transparent"


class DisplayConfig(BaseModel):
    mode: Literal["icon", "text", "gadget"] = "icon"
    image: str | None = None
    image_size: int | None = None
    gadget_type: Literal["gauge", "bar", "trafficlight"] | None = None
    gadget_metric: str | None = None


class StaticView(BaseModel):
    type: Literal["static"] = "static"


class WorldmapView(BaseModel):
    type: Literal["worldmap"] = "worldmap"
    lat: float = 51.0
    lng: float = 10.0
    zoom: int = 5


class RadarView(BaseModel):
    type: Literal["radar"] = "radar"
    filter: Literal["hostgroup", "servicegroup", "all_hosts", "all_services"] = "hostgroup"
    filter_value: str = ""


class AutomapView(BaseModel):
    type: Literal["automap"] = "automap"


BoardView = Annotated[
    Union[StaticView, WorldmapView, RadarView, AutomapView],
    Field(discriminator="type"),
]


class BoardObject(BaseModel):
    id: str
    type: ObjectType
    x: int | float = 0
    y: int | float = 0
    # Geographic coordinates (worldmap)
    lat: float | None = None
    lng: float | None = None
    z: int = 1
    # Host/Service specific
    host_name: str | None = None
    service_description: str | None = None
    # Group specific
    group_name: str | None = None
    # Map object
    map_name: str | None = None
    # Image source (separate from display.image which is for monitoring objects)
    image_src: str | None = None
    # Line endpoints
    x2: int | float | None = None
    y2: int | float | None = None
    line_style: LineStyle | None = None
    weathermap_metric: str | None = None
    # CMK label filter
    cmk_label_name: str | None = None
    cmk_label_value: str | None = None
    cmk_label_target: Literal["hosts", "services"] | None = None
    # Nested configs
    label: LabelConfig | None = Field(default_factory=LabelConfig)
    display: DisplayConfig | None = Field(default_factory=DisplayConfig)
    # Link
    url: str | None = None
    url_target: str = "_blank"
    # Templates (override board-global / global defaults)
    hover_template: str | None = None
    context_template: str | None = None


class BoardConfig(BaseModel):
    name: str
    alias: str = ""
    readonly: bool = False
    backend_id: str = "live_1"
    icon_size: int = 30
    rotation_interval: int = 0
    hover_template: str | None = None
    context_template: str | None = None
    background_image: str | None = None
    view: BoardView = Field(default_factory=StaticView)
    objects: list[BoardObject] = Field(default_factory=list)


class BoardCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9_\-]+$")
    alias: str = ""
    background_image: str | None = None
    icon_size: int = 30
    backend_id: str = "live_1"
    view: BoardView = Field(default_factory=StaticView)


class BoardUpdate(BaseModel):
    alias: str | None = None
    background_image: str | None = None
    icon_size: int | None = None
    backend_id: str | None = None
    view: BoardView | None = None
    hover_template: str | None = None
    context_template: str | None = None
    rotation_interval: int | None = None


class BoardRead(BaseModel):
    name: str
    alias: str
    background_image: str | None
    icon_size: int
    backend_id: str
    view_type: str
    view: BoardView
    object_count: int
    rotation_interval: int
    readonly: bool = False
    hover_template: str | None = None
    context_template: str | None = None


class BoardClone(BaseModel):
    new_name: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9_\-]+$")
    alias: str | None = None


class BoardPermissionsRead(BaseModel):
    """Which roles have view/edit access to a specific board (by name, not wildcard)."""
    view: list[str]
    edit: list[str]
