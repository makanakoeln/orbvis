"""Board configuration schemas."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field, field_validator

ObjectType = Literal[
    "host",
    "service",
    "hostgroup",
    "servicegroup",
    "map",
    "image",
    "line",
    "textbox",
    "cmk_label",
    "graph",
    "aggregation",
]


class AggregationInfo(BaseModel):
    """Discovery payload for a Checkmk BI aggregation (used by the editor autocomplete)."""

    id: str
    title: str
    pack_id: str


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


class FlowView(BaseModel):
    type: Literal["flow"] = "flow"


BoardView = Annotated[
    StaticView | WorldmapView | RadarView | FlowView,
    Field(discriminator="type"),
]

ClickAction = Literal["link", "none"]


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
    # Line endpoints (pixel for static, lat/lng for worldmap)
    x2: int | float | None = None
    y2: int | float | None = None
    lat2: float | None = None
    lng2: float | None = None
    line_style: LineStyle | None = None
    weathermap_metric: str | None = None
    # CMK label filter
    cmk_label_name: str | None = None
    cmk_label_value: str | None = None
    cmk_label_target: Literal["hosts", "services"] | None = None
    # Checkmk BI aggregation
    aggregation_id: str | None = None
    # State behaviour flags
    only_hard_states: bool = False
    recognize_services: bool = False
    # Member exclusion (hostgroup, servicegroup, host, map)
    exclude_members: str | None = None
    exclude_member_states: str | None = None
    # Nested configs
    label: LabelConfig | None = Field(default_factory=LabelConfig)
    display: DisplayConfig | None = Field(default_factory=DisplayConfig)
    # Label extensions
    label_border: str | None = None
    label_maxlen: int | None = None
    # Textbox styling
    textbox_background: str | None = None
    textbox_border: str | None = None
    textbox_width: int | None = None
    textbox_height: int | None = None
    # Graph embed
    graph_url: str | None = None
    graph_embed_type: Literal["img", "iframe"] = "img"
    graph_width: int = 400
    graph_height: int = 200
    graph_refresh_interval: int = 0
    graph_metric: list[str] | None = None
    graph_id: str | None = None
    graph_time_window: int | None = None  # minutes; None = all stored history

    @field_validator("graph_metric", mode="before")
    @classmethod
    def _coerce_graph_metric(cls, v: object) -> list[str] | None:
        # Backward compat: old saved configs may have a plain string value
        if isinstance(v, str):
            return [v] if v else None
        if v is None:
            return None
        if isinstance(v, list):
            return [s for s in v if isinstance(s, str)]
        return None

    # Line custom colors
    line_color: str | None = None
    line_color_border: str | None = None
    # Link
    url: str | None = None
    url_target: str = "_blank"
    # Hover URL (custom hover popup URL instead of template)
    hover_url: str | None = None
    # Templates (override board-global / global defaults)
    hover_template: str | None = None
    context_template: str | None = None


class BoardConfig(BaseModel):
    name: str
    alias: str = ""
    readonly: bool = False
    show_in_lists: bool = True
    backend_id: str = "live_1"
    icon_size: int = 30
    rotation_interval: int = 0
    sort_order: int = 0
    click_action: ClickAction = "link"
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
    sort_order: int | None = None
    click_action: ClickAction | None = None
    hover_template: str | None = None
    context_template: str | None = None
    rotation_interval: int | None = None
    show_in_lists: bool | None = None


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
    sort_order: int = 0
    click_action: ClickAction = "link"
    readonly: bool = False
    show_in_lists: bool = True
    hover_template: str | None = None
    context_template: str | None = None


class BoardObjectUpdate(BaseModel):
    """Allowed fields for a partial object update — id and type are immutable."""

    x: int | float | None = None
    y: int | float | None = None
    lat: float | None = None
    lng: float | None = None
    z: int | None = None
    host_name: str | None = None
    service_description: str | None = None
    group_name: str | None = None
    map_name: str | None = None
    image_src: str | None = None
    x2: int | float | None = None
    y2: int | float | None = None
    lat2: float | None = None
    lng2: float | None = None
    line_style: LineStyle | None = None
    weathermap_metric: str | None = None
    cmk_label_name: str | None = None
    cmk_label_value: str | None = None
    cmk_label_target: Literal["hosts", "services"] | None = None
    aggregation_id: str | None = None
    only_hard_states: bool | None = None
    recognize_services: bool | None = None
    exclude_members: str | None = None
    exclude_member_states: str | None = None
    label: LabelConfig | None = None
    display: DisplayConfig | None = None
    label_border: str | None = None
    label_maxlen: int | None = None
    textbox_background: str | None = None
    textbox_border: str | None = None
    textbox_width: int | None = None
    textbox_height: int | None = None
    graph_url: str | None = None
    graph_embed_type: Literal["img", "iframe"] | None = None
    graph_width: int | None = None
    graph_height: int | None = None
    graph_refresh_interval: int | None = None
    graph_metric: list[str] | None = None
    graph_id: str | None = None
    graph_time_window: int | None = None
    line_color: str | None = None
    line_color_border: str | None = None
    url: str | None = None
    url_target: str | None = None
    hover_url: str | None = None
    hover_template: str | None = None
    context_template: str | None = None


class BoardClone(BaseModel):
    new_name: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9_\-]+$")
    alias: str | None = None


class BoardPermissionsRead(BaseModel):
    """Which roles have view/edit access to a specific board (by name, not wildcard)."""

    view: list[str]
    edit: list[str]
