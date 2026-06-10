"""Board configuration schemas."""

from __future__ import annotations

import re
from typing import Annotated, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.schemas._validators import validate_user_url
from app.schemas.presentation import PresentationView


def _accept_legacy_backend_id(data: object) -> object:
    """Translate the pre-rename ``backend_id`` key to ``connection_id`` on input.

    Older board JSON files (written before the rename) carry ``backend_id``;
    the field name on the model is ``connection_id``. Run as a ``mode='before'``
    validator so the value reaches the canonical field, but never serialises
    back under the legacy name.
    """
    if isinstance(data, dict) and "backend_id" in data and "connection_id" not in data:
        data["connection_id"] = data.pop("backend_id")
    return data


# Hex (#rgb/#rgba/#rrggbb/#rrggbbaa), a plain CSS named color, or "transparent".
# Strict on purpose — keeps `<script>`, `javascript:`, `expression(...)` and other
# CSS-injection payloads out of stroke/background attributes downstream.
_COLOR_RE = re.compile(r"^(#[0-9a-fA-F]{3,8}|[a-zA-Z]{1,32}|transparent)$")


def _validate_color(value: str | None) -> str | None:
    if value is None or value == "":
        return value
    s = value.strip()
    if not _COLOR_RE.fullmatch(s):
        raise ValueError(f"invalid color value: {value!r}")
    return s


def _coerce_color(value: object) -> object:
    """Sanitize bad colors to ``None`` so legacy boards still load.

    Read-side companion to ``_validate_color`` — pre-existing JSON may carry
    values that newer rules reject (e.g. unsupported CSS expressions written
    before the validator existed). Dropping them is the safe fallback;
    re-saving the board through the API still rejects bad input.
    """
    if value is None or value == "":
        return value
    if not isinstance(value, str):
        return None
    return value if _COLOR_RE.fullmatch(value.strip()) else None


ObjectType = Literal[
    "host",
    "service",
    "hostgroup",
    "servicegroup",
    "dyngroup",
    "map",
    "image",
    "line",
    "textbox",
    "cmk_label",
    "graph",
    "aggregation",
]


# A dyngroup filter is forwarded to Livestatus. Only the safe filter-combinator
# headers may appear — anything else (Stats:, Columns:, OutputFormat:, GET,
# AuthUser:, …) would change the query semantics or exfiltrate data.
_SAFE_FILTER_LINE_RE = re.compile(r"^(?:Filter|And|Or|Negate): .+$")


def normalize_object_filter(value: str) -> str:
    """Validate and canonicalise a dyngroup Livestatus filter.

    NagVis stores filters with literal ``\\n`` separators and unescapes them at
    query time, so a single Filter: line often arrives without a real newline.
    We normalise to real newlines and require every logical line to be a safe
    combinator header — otherwise an escaped newline could smuggle in
    ``Stats:``/``Columns:``/``GET`` headers (the regex ``[^\\n]+`` previously let
    the literal ``\\n`` through untouched).
    """
    lines = [ln.strip() for ln in value.replace("\\n", "\n").splitlines() if ln.strip()]
    if not lines or not all(_SAFE_FILTER_LINE_RE.fullmatch(ln) for ln in lines):
        raise ValueError("object_filter must be one or more 'Filter: …' lines")
    return "\n".join(lines) + "\n"


class AggregationInfo(BaseModel):
    """Discovery payload for a Checkmk BI aggregation (used by the editor autocomplete)."""

    id: str
    title: str
    pack_id: str
    # Top-level aggregation function (worst / best / count_ok / call_a_rule
    # / state_of_host / state_of_service / ...). The EditPanel renders this
    # as a read-only chip so the designer doesn't have to crosscheck WATO
    # to know what semantic the aggregation has.
    function: str | None = None


class AggregationNode(BaseModel):
    """One node in a BI aggregation hierarchy (mirrors cmk.gui.nodevis output).

    ``node_type`` is ``"bi_aggregator"`` for rule nodes and ``"bi_leaf"`` for
    host/service leaves — same identifiers Checkmk uses, so frontend rendering
    can later be merged with cmk's node visualization. ``state`` is the BI
    integer state (0=OK, 1=WARN, 2=CRIT, 3=UNKNOWN).
    """

    name: str
    node_type: Literal["bi_aggregator", "bi_leaf"]
    state: int
    in_downtime: bool = False
    acknowledged: bool = False
    host_name: str | None = None
    service_description: str | None = None
    # Plugin output of the node's compute result (leaf check output for
    # bi_leaf nodes). Lets the drawer surface the worst leaf's output
    # without a second per-leaf fetch.
    output: str = ""
    children: list[AggregationNode] = Field(default_factory=list)


LineStyle = Literal[
    "plain",
    "arrow_end",
    "arrow_start",
    "arrow_both",
    "arrow_inward",
    "dashed",
]

# Which perfdata-derived label to render at the line's midpoint.
LinePerfdataLabel = Literal["none", "percent", "bandwidth", "both"]


def _migrate_weathermap(data: object) -> object:
    """Translate legacy ``line_style: weathermap`` to the new orthogonal model.

    The old monolithic style bundled three orthogonal aspects (bidirectional
    shape, bandwidth labels, utilization gradient). Stored boards using it
    are rewritten transparently during validation so old JSON keeps loading.
    """
    if isinstance(data, dict) and data.get("line_style") == "weathermap":
        migrated = {**data, "line_style": "arrow_inward"}
        migrated.setdefault("line_perfdata_label", "bandwidth")
        migrated.setdefault("line_weather_color", True)
        return migrated
    return data


class LabelConfig(BaseModel):
    show: bool = True
    text: str | None = None
    x: int = 0
    y: int = 0
    size: int = 11
    color: str = "#ffffff"
    background: str = "transparent"
    # NagVis label_width — fixed pixel width that wraps long labels.
    width: int | None = None
    weight: Literal["normal", "bold"] | None = None
    align: Literal["left", "right", "center", "justify"] | None = None


class DisplayConfig(BaseModel):
    mode: Literal["icon", "text", "gadget"] = "icon"
    image: str | None = None
    image_size: int | None = None
    gadget_type: Literal["gauge", "bar", "trafficlight"] | None = None
    gadget_metric: str | None = None


class StaticView(BaseModel):
    type: Literal["static"] = "static"
    problems_only: bool = False


class WorldmapView(BaseModel):
    type: Literal["worldmap"] = "worldmap"
    lat: float = 51.0
    lng: float = 10.0
    zoom: int = 5
    # Optional override for the Leaflet tile-URL template. Use ``{s}`` for
    # subdomain, ``{z}/{x}/{y}`` for tile coords. When omitted, the frontend
    # routes through OrbVis' own caching tile proxy (/api/v1/maps/tiles/...).
    tile_url: str | None = None
    # CSS saturate() filter percent: 0 = greyscale, 100 = unchanged.
    tile_saturate: float | None = Field(default=None, ge=0, le=100)
    # Automap source: when set, the backend dynamically populates the board
    # with hosts that carry orbvis_lat/orbvis_lng labels (or legacy LAT/LONG
    # custom variables) from the configured connection. Persisted objects
    # remain visible on top of the auto-discovered ones.
    auto_source: Literal["all_hosts", "hostgroup", "servicegroup"] | None = None
    auto_filter_value: str = ""
    problems_only: bool = False


class RadarView(BaseModel):
    type: Literal["radar"] = "radar"
    filter: Literal["hostgroup", "servicegroup", "all_hosts", "all_services"] = "hostgroup"
    filter_value: str = ""
    problems_only: bool = False


class FlowNodePosition(BaseModel):
    x: float
    y: float


class FlowView(BaseModel):
    type: Literal["flow"] = "flow"
    root: str | None = None
    # -1 = unlimited; None defaults to unlimited downward / 0 upward (NagVis automap defaults).
    child_layers: int | None = Field(default=None, ge=-1, le=20)
    parent_layers: int | None = Field(default=None, ge=-1, le=20)
    # Per-board overrides for the global flow_board_* limits. None = use the
    # global default from settings.
    top_affected_hosts: int | None = Field(default=None, ge=0, le=1000)
    max_services_per_host: int | None = Field(default=None, ge=0, le=500)
    # Pinned host positions from operator drags. Key is the host name; missing
    # hosts fall back to the force-simulation layout. Service-node positions
    # are derived from their host and not persisted.
    positions: dict[str, FlowNodePosition] = Field(default_factory=dict)
    # Service-node layout chosen by the operator. None = use UI default.
    service_layout: Literal["off", "donut", "fan", "orbit", "row"] | None = None
    problems_only: bool = False


class FolderTreeView(BaseModel):
    type: Literal["foldertree"] = "foldertree"
    # Stable WATO folder ``__id`` (preferred, survives rename/move) or path slug
    # ("" = root / all folders). See concept v3 §7.1.
    root_folder: str = ""
    # Which presentation the board opens in (operator-chosen, saved per board).
    # Defaults to the treemap — the glanceable status surface; list is secondary.
    default_view: Literal["list", "map"] = "map"
    default_expand_depth: int = Field(default=1, ge=0, le=20)
    show_services: bool = False
    show_empty_folders: bool = True
    problems_only: bool = False
    # What counts as a "problem" for the problems_only filter. On typical
    # sites almost every host carries some WARNING service, so "any" barely
    # filters; "critical" narrows to CRITICAL/DOWN/UNREACHABLE.
    problems_severity: Literal["any", "critical"] = "any"
    only_hard_states: bool = False
    # Distributed monitoring: scope to these site ids; empty = all sites (v3 §5).
    sites: list[str] = Field(default_factory=list)


BoardView = Annotated[
    StaticView | WorldmapView | RadarView | FlowView | FolderTreeView | PresentationView,
    Field(discriminator="type"),
]


def view_element_count(view: BoardView) -> int:
    """Object count for a board's list/read payload.

    Presentation boards keep ``BoardConfig.objects`` empty and carry their
    content as ``view.elements`` instead, so count those for them.
    """
    if isinstance(view, PresentationView):
        return len(view.elements)
    return 0


ClickAction = Literal["link", "none"]
RenderMode = Literal["default", "nagvis_classic"]


class BoardObject(BaseModel):
    id: str
    type: ObjectType
    # Per-object connection override. ``None`` means "inherit the board's
    # connection_id" — the common case. Setting this lets a single board mix
    # objects from multiple monitoring backends, the way NagVis allows
    # ``backend_id`` per object.
    connection_id: str | None = None
    x: int | float = 0
    y: int | float = 0
    lat: float | None = None
    lng: float | None = None
    # ``None`` means "inherit the board's ``default_z``" — NagVis stores no z on
    # objects that use the global default, so imported objects stay unset and
    # the renderer resolves ``z ?? board.default_z``.
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
    # Optional line bend/meeting point. ``None`` → renderer uses the geometric
    # midpoint of the two endpoints (the previous fixed behavior). A set value
    # mirrors NagVis' explicit middle coordinate on two-segment lines.
    mid_x: int | float | None = None
    mid_y: int | float | None = None
    # Line endpoint bindings: when set, the start/end follows the referenced
    # object's position instead of a fixed coordinate (sticky connectors).
    start_ref: str | None = None
    end_ref: str | None = None
    line_style: LineStyle | None = None
    # Stroke width in pixels. None → renderer's per-style default.
    line_width: int | None = Field(default=None, ge=1, le=20)
    # Which perfdata label to draw at the line midpoint (none/percent/bandwidth/both).
    line_perfdata_label: LinePerfdataLabel = "none"
    # Color the line by inbound/outbound utilization gradient instead of state color.
    line_weather_color: bool = False
    # Inbound metric (rendered left of the midpoint).
    weathermap_metric: str | None = None
    # Outbound metric (rendered right of the midpoint).
    weathermap_metric_out: str | None = None
    cmk_label_name: str | None = None
    cmk_label_value: str | None = None
    cmk_label_target: Literal["hosts", "services"] | None = None
    aggregation_id: str | None = None
    # Dyngroup: arbitrary Livestatus filter producing a set of hosts/services.
    object_types: Literal["host", "service"] | None = None
    object_filter: str | None = None
    # 0 = root only, hard cap 10 levels — see backend.app.services.state_service.
    expand_depth: int = Field(default=0, ge=0, le=10)
    only_hard_states: bool = False
    recognize_services: bool = False
    exclude_members: str | None = None
    exclude_member_states: str | None = None
    label: LabelConfig | None = Field(default_factory=LabelConfig)
    display: DisplayConfig | None = Field(default_factory=DisplayConfig)
    label_border: str | None = None
    label_maxlen: int | None = None
    textbox_background: str | None = None
    textbox_border: str | None = None
    textbox_width: int | None = None
    textbox_height: int | None = None
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

    @field_validator("url", "hover_url", "graph_url")
    @classmethod
    def _validate_urls(cls, v: str | None) -> str | None:
        return validate_user_url(v)

    @field_validator("line_color", "line_color_border")
    @classmethod
    def _validate_line_colors(cls, v: str | None) -> str | None:
        return _validate_color(v)

    @field_validator("object_filter")
    @classmethod
    def _validate_object_filter(cls, v: str | None) -> str | None:
        if v is None or not v.strip():
            return None
        return normalize_object_filter(v)

    @model_validator(mode="before")
    @classmethod
    def _legacy_weathermap(cls, data: object) -> object:
        return _migrate_weathermap(data)

    line_color: str | None = None
    line_color_border: str | None = None
    url: str | None = None
    url_target: str = "_blank"
    hover_url: str | None = None
    hover_template: str | None = None
    context_template: str | None = None


class BoardConfig(BaseModel):
    _migrate_legacy_keys = model_validator(mode="before")(_accept_legacy_backend_id)

    name: str
    alias: str = ""
    readonly: bool = False
    show_in_lists: bool = True
    connection_id: str = "live_1"
    icon_size: int | None = None
    rotation_interval: int = 0
    sort_order: int = 0
    click_action: ClickAction = "link"
    hover_template: str | None = None
    context_template: str | None = None
    background_image: str | None = None
    background_color: str | None = None
    # Default keeps existing boards on the OrbVis renderer; "nagvis_classic"
    # opts an imported board into top-left anchoring + flat styling.
    render_mode: RenderMode = "default"
    # Board-wide fallback z for objects that carry no explicit ``z`` (mirrors
    # NagVis' global default). Default 1 preserves the historic per-object
    # default; the cfg importer writes 10 to match NagVis exactly.
    default_z: int = 1
    # Monotonically incremented per persisted change. Compared against the
    # client's ``If-Match`` header on update; mismatch returns 409 Conflict so
    # two operators editing the same board don't silently lose changes.
    version: int = 0
    view: BoardView = Field(default_factory=StaticView)
    objects: list[BoardObject] = Field(default_factory=list)


class BoardCreate(BaseModel):
    _migrate_legacy_keys = model_validator(mode="before")(_accept_legacy_backend_id)

    name: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9_\-]+$")
    alias: str = ""
    background_image: str | None = None
    background_color: str | None = None
    icon_size: int | None = None
    connection_id: str = "live_1"
    view: BoardView = Field(default_factory=StaticView)
    render_mode: RenderMode = "default"
    default_z: int = 1


class BoardUpdate(BaseModel):
    _migrate_legacy_keys = model_validator(mode="before")(_accept_legacy_backend_id)

    alias: str | None = None
    background_image: str | None = None
    background_color: str | None = None
    icon_size: int | None = None
    connection_id: str | None = None
    view: BoardView | None = None
    sort_order: int | None = None
    click_action: ClickAction | None = None
    hover_template: str | None = None
    context_template: str | None = None
    rotation_interval: int | None = None
    show_in_lists: bool | None = None
    render_mode: RenderMode | None = None
    default_z: int | None = None


class BoardOrderItem(BaseModel):
    name: str
    sort_order: int


class BoardRead(BaseModel):
    _migrate_legacy_keys = model_validator(mode="before")(_accept_legacy_backend_id)

    name: str
    alias: str
    background_image: str | None
    background_color: str | None = None
    icon_size: int | None
    connection_id: str
    view_type: str
    view: BoardView
    object_count: int
    rotation_interval: int
    version: int = 0
    sort_order: int = 0
    click_action: ClickAction = "link"
    readonly: bool = False
    show_in_lists: bool = True
    hover_template: str | None = None
    context_template: str | None = None
    render_mode: RenderMode = "default"
    default_z: int = 1
    # Per-user capability stamped by the list endpoint: whether the requesting
    # user may edit this board (admins, or non-admins with edit permission).
    can_edit: bool = False


class BoardObjectUpdate(BaseModel):
    """Allowed fields for a partial object update — id and type are immutable."""

    connection_id: str | None = None
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
    mid_x: int | float | None = None
    mid_y: int | float | None = None
    start_ref: str | None = None
    end_ref: str | None = None
    line_style: LineStyle | None = None
    line_width: int | None = Field(default=None, ge=1, le=20)
    line_perfdata_label: LinePerfdataLabel | None = None
    line_weather_color: bool | None = None
    weathermap_metric: str | None = None
    weathermap_metric_out: str | None = None
    cmk_label_name: str | None = None
    cmk_label_value: str | None = None
    cmk_label_target: Literal["hosts", "services"] | None = None
    aggregation_id: str | None = None
    object_types: Literal["host", "service"] | None = None
    object_filter: str | None = None
    expand_depth: int | None = Field(default=None, ge=0, le=10)
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

    @field_validator("url", "hover_url", "graph_url")
    @classmethod
    def _validate_urls(cls, v: str | None) -> str | None:
        return validate_user_url(v)

    @field_validator("line_color", "line_color_border")
    @classmethod
    def _validate_line_colors(cls, v: str | None) -> str | None:
        return _validate_color(v)

    @field_validator("object_filter")
    @classmethod
    def _validate_object_filter(cls, v: str | None) -> str | None:
        if v is None or not v.strip():
            return None
        return normalize_object_filter(v)

    @model_validator(mode="before")
    @classmethod
    def _legacy_weathermap(cls, data: object) -> object:
        return _migrate_weathermap(data)


class BoardClone(BaseModel):
    new_name: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9_\-]+$")
    alias: str | None = None


class BoardPermissionsRead(BaseModel):
    """Which roles have view/edit access to a specific board (by name, not wildcard)."""

    view: list[str]
    edit: list[str]


_BoardNameStr = Annotated[str, Field(min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9_\-]+$")]


class BoardBulkDelete(BaseModel):
    names: Annotated[list[_BoardNameStr], Field(min_length=1, max_length=500)]


class BoardBulkDeleteFailure(BaseModel):
    name: str
    reason: str


class BoardBulkDeleteResult(BaseModel):
    deleted: list[str]
    failed: list[BoardBulkDeleteFailure]


class BoardBulkEdit(BaseModel):
    names: Annotated[list[_BoardNameStr], Field(min_length=1, max_length=500)]
    # Untyped dict on purpose: the API layer first runs the FormSpec wire
    # conversions (rotation cascading → int, click_action bool → literal)
    # and then validates the resulting subset against ``BoardUpdate``.
    updates: dict[str, object]


class BoardBulkEditFailure(BaseModel):
    name: str
    reason: str


class BoardBulkEditResult(BaseModel):
    updated: list[str]
    failed: list[BoardBulkEditFailure]


class BoardBulkExport(BaseModel):
    names: Annotated[list[_BoardNameStr], Field(min_length=1, max_length=500)]
