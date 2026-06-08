"""Parse legacy .cfg map content and convert it to an OrbVis board dict.

Used by the import API endpoint; the standalone CLI (tools/cfg_importer.py)
contains its own copy of the same logic so it stays dependency-free.
"""

from __future__ import annotations

import re

# Legacy line_type integers from the .cfg map format. 13/14/15 only appear on
# stateful lines (service block with view_type=line); 20 is not a valid value.
# Each entry decomposes the legacy line_type into the orthogonal OrbVis fields:
# shape (line_style), perfdata-label mode, and weather-color flag.
LINE_TYPE_MAP: dict[int, dict[str, object]] = {
    10: {"line_style": "arrow_inward"},  # -------><------- bidirectional
    11: {"line_style": "arrow_end"},  # --------------->
    12: {"line_style": "plain"},  # ---------------- no arrows
    13: {  # ---%---><---%--- percent labels + utilization gradient
        "line_style": "arrow_inward",
        "line_perfdata_label": "percent",
        "line_weather_color": True,
    },
    14: {  # --%+BW-><-%+BW-- percent + bandwidth labels + gradient
        "line_style": "arrow_inward",
        "line_perfdata_label": "both",
        "line_weather_color": True,
    },
    15: {  # ---BW--><--BW--- bandwidth labels + gradient
        "line_style": "arrow_inward",
        "line_perfdata_label": "bandwidth",
        "line_weather_color": True,
    },
}
_DEFAULT_LINE_TYPE = LINE_TYPE_MAP[11]

ICONSET_SIZE: dict[str, int] = {
    "std_big": 30,
    "std_medium": 24,
    "std": 22,
    "std_small": 16,
}

_FRAMESET_TARGETS = {"main", "frames", "main_window"}

# Stock legacy gadget URL → OrbVis gadget_type. Custom/unknown gadget_urls
# fall back to icon mode silently — there is no equivalent OrbVis renderer.
_GADGET_URL_MAP: dict[str, str] = {
    "std_speedometer.php": "gauge",
    "std_speedometer2.php": "gauge",
    "std_bar.php": "bar",
    "std_html_bar.php": "bar",
}


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


def _parse_blocks(text: str) -> list[tuple[str, dict[str, str]]]:
    text = re.sub(r"(?m)^\s*#[^\n]*", "", text)
    text = re.sub(r"(?m)^\s*;[^\n]*", "", text)
    blocks = []
    for m in re.finditer(r"define\s+(\w+)\s*\{([^}]*)\}", text, re.DOTALL):
        block_type = m.group(1).strip().lower()
        props: dict[str, str] = {}
        for line in m.group(2).splitlines():
            line = line.strip()
            kv = re.match(r"(\w+)\s*=\s*(.*)", line)
            if kv:
                props[kv.group(1).strip()] = kv.group(2).strip()
        blocks.append((block_type, props))
    return blocks


def _int(v: str | None, default: int = 0) -> int:
    try:
        return int(v) if v is not None else default
    except ValueError:
        return default


def _bool(v: str | None, default: bool = False) -> bool:
    return (v or "").strip().lower() in ("1", "true", "yes") if v is not None else default


_REL_COORD_RE = re.compile(r"^([A-Za-z0-9_]+)%([+-]?\d+)$")
_PERCENT_COORD_RE = re.compile(r"^[+-]?\d+%([+-]?\d+)$")


class _Coord:
    """NagVis coordinate. ``ref`` is the referenced object_id if relative."""

    __slots__ = ("offset", "ref", "value")

    def __init__(self, value: int, ref: str | None = None, offset: int | None = None):
        self.value = value
        self.ref = ref
        self.offset = offset


def _parse_coord(v: str) -> _Coord:
    v = v.strip()
    if v.lstrip("-").isdigit():
        return _Coord(int(v))
    # Percent-of-canvas (legacy NagVis "50%100" = 50% + 100 offset) collapses
    # to the offset; the percent portion of the original viewport reference is
    # dropped, matching pre-existing behaviour.
    m = _PERCENT_COORD_RE.match(v)
    if m:
        return _Coord(int(m.group(1)))
    m = _REL_COORD_RE.match(v)
    if m:
        return _Coord(value=int(m.group(2)), ref=m.group(1), offset=int(m.group(2)))
    return _Coord(0)


def _coord(v: str) -> int:
    return _parse_coord(v).value


def _attach_pending(obj: dict[str, object], **coords: _Coord) -> None:
    refs = {k: c for k, c in coords.items() if c.ref is not None}
    if refs:
        obj["_pending_refs"] = {k: {"ref": c.ref, "offset": c.offset or 0} for k, c in refs.items()}


def _set_explicit_z(obj: dict[str, object], p: dict[str, str]) -> None:
    """Write ``z`` only when the cfg block set it explicitly.

    NagVis stores no z on objects that use its global default (10); leaving z
    unset lets such objects inherit the board's ``default_z`` instead of each
    type inventing its own layer — reproducing NagVis layering 1:1.
    """
    if "z" in p:
        obj["z"] = _int(p["z"])


def _resolve_pending_refs(objects: list[dict[str, object]]) -> None:
    """Resolve ``_pending_refs`` against the raw NagVis object_id index.

    Iterates up to 5 passes so transitive chains (A → B → C) settle; NagVis
    itself warns about cycles so deeper chains are unexpected.
    """
    by_raw: dict[str, dict[str, object]] = {}
    for obj in objects:
        raw_id = str(obj.get("id", "")).split("_", 1)[-1]
        if raw_id:
            by_raw[raw_id] = obj
    for _ in range(5):
        changed = False
        for obj in objects:
            refs = obj.get("_pending_refs")
            if not isinstance(refs, dict):
                continue
            for axis, ref in list(refs.items()):
                target = by_raw.get(ref["ref"])
                if target is None:
                    continue
                # x2/y2/mid_x reuse the target's x/y — NagVis only stores one
                # endpoint per object, lines reuse it by axis-name match.
                base_axis = "x" if axis in ("x", "x2", "mid_x") else "y"
                target_refs = target.get("_pending_refs")
                if isinstance(target_refs, dict) and base_axis in target_refs:
                    continue
                base_val = target.get(base_axis, 0)
                assert isinstance(base_val, int)
                obj[axis] = base_val + int(ref["offset"])
                refs.pop(axis)
                changed = True
            if not refs:
                obj.pop("_pending_refs", None)
        if not changed:
            break
    for obj in objects:
        obj.pop("_pending_refs", None)


def _axis_coords(raw: str, fallback_second: str) -> tuple[_Coord, _Coord, _Coord | None]:
    """Parse one axis of a line into (start, end, optional bend).

    NagVis encodes a line's coords as a comma-separated list per axis. With
    three values (a two-segment line) the middle is the bend/meeting point;
    first and last are always the endpoints. Falls back to a separate
    ``x2``/``y2`` key when no comma is present.
    """
    if "," in raw:
        parts = [s.strip() for s in raw.split(",")]
        mid = _parse_coord(parts[1]) if len(parts) >= 3 else None
        return _parse_coord(parts[0]), _parse_coord(parts[-1]), mid
    return _parse_coord(raw), _parse_coord(fallback_second), None


def _line_coords(
    p: dict[str, str],
) -> tuple[_Coord, _Coord, _Coord, _Coord, _Coord | None, _Coord | None]:
    x, x2, mid_x = _axis_coords(p.get("x", "0"), p.get("x2", "0"))
    y, y2, mid_y = _axis_coords(p.get("y", "0"), p.get("y2", "0"))
    return x, y, x2, y2, mid_x, mid_y


# NagVis [name] macro resolves to the object identifier; OrbVis uses
# {{name}}. Dropping the label lets the renderer fall back to host_name
# rather than printing the literal token.
_BARE_NAME_RE = re.compile(r"^\s*\[name\]\s*$")


def _label_text(raw: str | None) -> str | None:
    if not raw:
        return None
    if _BARE_NAME_RE.match(raw):
        return None
    return raw


def _label_x(raw: str | None) -> int:
    """Parse legacy ``label_x``. NagVis allows ``center`` to mean 0-offset."""
    if raw is None:
        return 0
    v = raw.strip().lower()
    if v == "center":
        return 0
    try:
        return int(v.lstrip("+"))
    except ValueError:
        return 0


def _bg_brightness(value: str | None) -> float | None:
    if not value:
        return None
    v = value.strip().lower()
    if v in {"transparent", ""}:
        return None
    if v.startswith("#") and len(v) in (4, 7):
        try:
            if len(v) == 4:
                r, g, b = (int(c * 2, 16) for c in v[1:])
            else:
                r, g, b = int(v[1:3], 16), int(v[3:5], 16), int(v[5:7], 16)
        except ValueError:
            return None
        return (r + g + b) / 3
    return None


def _bg_is_opaque_light(value: str | None) -> bool:
    b = _bg_brightness(value)
    return b is not None and b > 180


def _bg_is_opaque_dark(value: str | None) -> bool:
    b = _bg_brightness(value)
    return b is not None and b < 100


def _label_y(raw: str | None) -> int:
    """Parse legacy ``label_y``.

    NagVis defaults to ``bottom`` which places the label top flush with the
    icon's bottom edge — that's ``label_top = object_y + icon_height``. With
    OrbVis' 22-px default icon that's 22. Anything explicit (``+25``, ``-3``,
    ``0``) is honoured as a relative pixel offset.
    """
    if raw is None:
        return 22
    v = raw.strip().lower()
    if v in ("", "bottom"):
        return 22
    if v == "top":
        return 0
    if v == "center":
        return -11
    try:
        return int(v.lstrip("+"))
    except ValueError:
        return 22


def _label(p: dict[str, str], *, show_default: bool = True) -> dict[str, object]:
    raw_bg = p.get("label_background", "transparent")
    # NagVis canvas is light, so default to black; flip only for opaque-dark bg.
    default_color = "#ffffff" if _bg_is_opaque_dark(raw_bg) else "#000000"
    return {
        "show": _bool(p.get("label_show"), show_default),
        "text": _label_text(p.get("label_text")),
        "x": _label_x(p.get("label_x")),
        "y": _label_y(p.get("label_y")),
        "size": _int(p.get("label_size"), 11),
        "color": p.get("label_color", default_color),
        "background": raw_bg,
        "width": _int(p.get("label_width")) or None,
    }


# ---------------------------------------------------------------------------
# Converter
# ---------------------------------------------------------------------------


_BLOCK_TYPES = frozenset(
    {
        "host",
        "service",
        "hostgroup",
        "servicegroup",
        "dyngroup",
        "map",
        "shape",
        "line",
        "textbox",
        "aggr",
    }
)

# Keys identifying a block — never inherited from a template/global layer.
_NON_INHERITED_KEYS = frozenset({"object_id", "name", "template"})

# Global-block keys that configure the board itself (handled by _apply_global)
# and must not be pushed onto every object as a default. backend_id stays
# board-level so objects only get a per-object override when set explicitly.
# view_type is excluded too: a global view_type=line would reroute every host
# into the line handler — view_type is inherited from templates (line/gadget
# templates), never from global.
_GLOBAL_BOARD_KEYS = frozenset(
    {
        "alias",
        "map_image",
        "background_color",
        "backend_id",
        "connection_id",
        "iconset",
        "sources",
        "root",
        "child_layers",
        "parent_layers",
        "view_type",
    }
)


def _apply_global(board: dict[str, object], p: dict[str, str]) -> None:
    if "alias" in p:
        board["alias"] = p["alias"]
    if "map_image" in p:
        board["background_image"] = p["map_image"]
    # NagVis cfg uses the legacy "backend_id" parameter name on disk; map to our
    # canonical "connection_id" while reading.
    if "backend_id" in p:
        board["connection_id"] = p["backend_id"]
    if "iconset" in p:
        board["icon_size"] = ICONSET_SIZE.get(p["iconset"], 22)

    sources = {s.strip().lower() for s in p.get("sources", "").split(",") if s.strip()}
    if "automap" in sources:
        view: dict[str, object] = {"type": "flow"}
        if p.get("root"):
            view["root"] = p["root"]
        if "child_layers" in p:
            view["child_layers"] = _int(p["child_layers"], -1)
        if "parent_layers" in p:
            view["parent_layers"] = _int(p["parent_layers"], 0)
        board["view"] = view


def _line_obj_common(p: dict[str, str], raw_id: str) -> dict[str, object]:
    x, y, x2, y2, mid_x, mid_y = _line_coords(p)
    type_attrs = LINE_TYPE_MAP.get(_int(p.get("line_type", "11")), _DEFAULT_LINE_TYPE)
    obj: dict[str, object] = {
        "id": f"line_{raw_id}",
        "type": "line",
        "x": x.value,
        "y": y.value,
        "x2": x2.value,
        "y2": y2.value,
        "label": {"show": False},
        # NagVis default line_color_border = #000000; renders the colored fill
        # over a black outline.
        "line_color_border": (p.get("line_color_border") or "").strip() or "#000000",
        **type_attrs,
    }
    _set_explicit_z(obj, p)
    refs = {"x": x, "y": y, "x2": x2, "y2": y2}
    # Explicit bend/meeting point (NagVis stored the middle of a 3-coord line).
    if mid_x is not None and mid_y is not None:
        obj["mid_x"] = mid_x.value
        obj["mid_y"] = mid_y.value
        refs["mid_x"] = mid_x
        refs["mid_y"] = mid_y
    _attach_pending(obj, **refs)
    # NagVis line_width is the polygon half-width (-w to +w); OrbVis renders
    # it as full stroke width. Double on import.
    obj["line_width"] = _int(p.get("line_width"), 3) * 2
    return obj


def _apply_weathermap_defaults(obj: dict[str, object]) -> None:
    """Give weathermap lines NagVis' implicit in/out metric defaults.

    NagVis needs no metric configuration: line_label_in/line_label_out default
    to "in"/"out" and are matched against the bound service's perfdata. OrbVis
    requires an explicit weathermap_metric, so mirror that default — otherwise
    imported weathermap lines have the gradient enabled but no metric to read
    and stay uncolored.
    """
    if not obj.get("line_weather_color"):
        return
    obj.setdefault("weathermap_metric", "in")
    obj.setdefault("weathermap_metric_out", "out")


def _handle_view_type_line(p: dict[str, str], raw_id: str) -> dict[str, object]:
    """Service/host block with view_type=line — render as a line.

    Legacy format encodes a line this way; recognising it explicitly avoids
    the icon path treating the comma-separated x/y as broken coords.
    """
    obj = _line_obj_common(p, raw_id)
    if "host_name" in p:
        obj["host_name"] = p["host_name"]
    if "service_description" in p:
        obj["service_description"] = p["service_description"]
    # Legacy: line_label_in/out name the inbound/outbound perfdata fields so
    # the bandwidth labels can render flanking the midpoint.
    if "line_label_in" in p:
        obj["weathermap_metric"] = p["line_label_in"]
    if "line_label_out" in p:
        obj["weathermap_metric_out"] = p["line_label_out"]
    _apply_weathermap_defaults(obj)
    return obj


def _handle_line_block(p: dict[str, str], raw_id: str) -> dict[str, object]:
    obj = _line_obj_common(p, raw_id)
    # Stateful line variants (13/14/15) — bind to host/service so live
    # bandwidth and weather-color have data to read from.
    if obj.get("line_perfdata_label") not in (None, "none"):
        if "host_name" in p:
            obj["host_name"] = p["host_name"]
        if "service_description" in p:
            obj["service_description"] = p["service_description"]
        if "weathermap_metric" in p:
            obj["weathermap_metric"] = p["weathermap_metric"]
        if "weathermap_metric_out" in p:
            obj["weathermap_metric_out"] = p["weathermap_metric_out"]
    _apply_weathermap_defaults(obj)
    return obj


def _handle_shape(p: dict[str, str], raw_id: str) -> dict[str, object]:
    x, y = _parse_coord(p.get("x", "0")), _parse_coord(p.get("y", "0"))
    obj: dict[str, object] = {
        "id": f"image_{raw_id}",
        "type": "image",
        "x": x.value,
        "y": y.value,
        "image_src": p.get("icon") or None,
        "label": {"show": False},
    }
    _set_explicit_z(obj, p)
    _attach_pending(obj, x=x, y=y)
    return obj


# HTML <font size="N"> maps to fixed pixel sizes (legacy spec).
_FONT_SIZE_HTML = {"1": 10, "2": 13, "3": 16, "4": 18, "5": 24, "6": 32, "7": 48}
_FONT_SIZE_KEYWORD = {
    "xx-small": 9,
    "x-small": 10,
    "small": 13,
    "medium": 16,
    "large": 18,
    "x-large": 24,
    "xx-large": 32,
}
_ENTITY_RE = re.compile(r"&(?:amp|lt|gt|quot|nbsp|#39|apos);")
_ENTITY_MAP = {
    "&amp;": "&",
    "&lt;": "<",
    "&gt;": ">",
    "&quot;": '"',
    "&nbsp;": " ",
    "&#39;": "'",
    "&apos;": "'",
}


def _decode_html_entities(text: str) -> str:
    return _ENTITY_RE.sub(lambda m: _ENTITY_MAP.get(m.group(0), m.group(0)), text)


def _extract_html_style(html: str) -> dict[str, object]:
    """Pull color/font-size/weight/text-align from inline HTML in a textbox."""
    out: dict[str, object] = {}
    m = re.search(r'<font[^>]*color=["\']([^"\']+)', html, re.IGNORECASE)
    if not m:
        # Lookbehind keeps `background-color:` from matching as a `color:` suffix.
        m = re.search(r'(?<![-\w])color\s*:\s*([^;"\']+)', html, re.IGNORECASE)
    if m:
        out["color"] = m.group(1).strip()
    m = re.search(r'font-size\s*:\s*([^;"\']+)', html, re.IGNORECASE)
    if m:
        v = m.group(1).strip().lower()
        if v.endswith("px"):
            try:
                out["size"] = int(float(v[:-2]))
            except ValueError:
                pass
        elif v in _FONT_SIZE_KEYWORD:
            out["size"] = _FONT_SIZE_KEYWORD[v]
    elif m := re.search(r'<font[^>]*\bsize=["\']?([1-7])', html, re.IGNORECASE):
        out["size"] = _FONT_SIZE_HTML[m.group(1)]
    if re.search(r"<b\b", html, re.IGNORECASE) or re.search(
        r"font-weight\s*:\s*bold", html, re.IGNORECASE
    ):
        out["weight"] = "bold"
    m = re.search(r"text-align\s*:\s*(left|right|center|justify)", html, re.IGNORECASE)
    if m:
        out["align"] = m.group(1).lower()
    return out


def _handle_textbox(p: dict[str, str], raw_id: str) -> dict[str, object]:
    raw_text = p.get("text") or None
    html_style: dict[str, object] = {}
    if raw_text:
        html_style = _extract_html_style(raw_text)
        raw_text = re.sub(r"<br\s*/?>", "\n", raw_text, flags=re.IGNORECASE)
        raw_text = re.sub(r"<[^>]+>", "", raw_text)
        raw_text = _decode_html_entities(raw_text)
    width = (
        _int(p.get("w"), 200) if (p.get("w") or "").strip().lower() not in {"auto", ""} else None
    )
    height = (
        _int(p.get("h"), 40) if (p.get("h") or "").strip().lower() not in {"auto", ""} else None
    )
    # nagvis_classic anchors top-left; keep raw NagVis coords for 1:1 layout.
    tx = _parse_coord(p.get("x", "0"))
    ty = _parse_coord(p.get("y", "0"))
    label: dict[str, object] = {
        "show": True,
        "text": raw_text,
        "x": 0,
        "y": 0,
        "size": html_style.get("size", 11),
        "color": html_style.get("color", "#000000"),
        "background": "transparent",
    }
    if "weight" in html_style:
        label["weight"] = html_style["weight"]
    if "align" in html_style:
        label["align"] = html_style["align"]
    obj: dict[str, object] = {
        "id": f"textbox_{raw_id}",
        "type": "textbox",
        "x": tx.value,
        "y": ty.value,
        "label": label,
        # NagVis default is transparent; lets lines drawn under the textbox
        # stay visible on the white canvas.
        "textbox_background": (p.get("background_color") or "").strip() or "transparent",
    }
    _set_explicit_z(obj, p)
    _attach_pending(obj, x=tx, y=ty)
    if width is not None:
        obj["textbox_width"] = width
    if height is not None:
        obj["textbox_height"] = height
    # NagVis textbox border_color default is #e5e5e5 (light gray); explicit
    # #000000 in cfg renders prominent black, unset stays subtle.
    obj["textbox_border"] = (p.get("border_color") or "").strip() or "#e5e5e5"
    return obj


def _build_display(p: dict[str, str]) -> dict[str, object]:
    mode = p.get("view_type", "icon")
    if mode not in ("icon", "text", "gadget"):
        mode = "icon"
    if mode != "gadget":
        return {"mode": mode}
    # Legacy default for an unset gadget_url is the speedometer; render as gauge.
    # Unknown values fall back to icon so the object stays visible.
    gadget_url = p.get("gadget_url", "").strip()
    gadget_type = _GADGET_URL_MAP.get(gadget_url)
    if gadget_type is None and gadget_url == "":
        gadget_type = "gauge"
    if gadget_type is None:
        return {"mode": "icon"}
    return {"mode": "gadget", "gadget_type": gadget_type, "gadget_metric": None}


def _apply_type_specific(obj: dict[str, object], block_type: str, p: dict[str, str]) -> None:
    if block_type == "host":
        obj["host_name"] = p.get("host_name")
        if _bool(p.get("only_hard_states")):
            obj["only_hard_states"] = True
        if _bool(p.get("recognize_services")):
            obj["recognize_services"] = True
    elif block_type == "service":
        obj["host_name"] = p.get("host_name")
        obj["service_description"] = p.get("service_description")
        if _bool(p.get("only_hard_states")):
            obj["only_hard_states"] = True
    elif block_type == "hostgroup":
        obj["group_name"] = p.get("hostgroup_name") or p.get("group_name")
    elif block_type == "servicegroup":
        obj["group_name"] = p.get("servicegroup_name") or p.get("group_name")
    elif block_type == "map":
        obj["map_name"] = p.get("map_name")
    elif block_type == "aggr":
        # Newer .cfg exports write 'name='; older CLI imports used 'aggr_name='.
        obj["aggregation_id"] = p.get("aggr_name") or p.get("name")
        if "aggr_url" in p and "url" not in p:
            obj["url"] = p["aggr_url"]
    elif block_type == "dyngroup":
        ot = (p.get("object_types") or "host").strip().lower()
        obj["object_types"] = "service" if ot == "service" else "host"
        obj["object_filter"] = p.get("object_filter") or None


def _handle_monitor_block(block_type: str, p: dict[str, str], raw_id: str) -> dict[str, object]:
    """host / service / hostgroup / servicegroup / map / aggr."""
    orbvis_type = "aggregation" if block_type == "aggr" else block_type
    x, y = _parse_coord(p.get("x", "0")), _parse_coord(p.get("y", "0"))
    obj: dict[str, object] = {
        "id": f"{orbvis_type}_{raw_id}",
        "type": orbvis_type,
        "x": x.value,
        "y": y.value,
        "label": _label(p),
        "display": _build_display(p),
        # NagVis .box CSS draws every label with a 1px solid border (#e5e5e5).
        "label_border": (p.get("label_border") or "#e5e5e5").strip(),
    }
    _set_explicit_z(obj, p)
    _attach_pending(obj, x=x, y=y)
    _apply_type_specific(obj, block_type, p)
    if "url" in p:
        obj["url"] = p["url"]
    if "url_target" in p:
        raw_target = p["url_target"]
        obj["url_target"] = "_blank" if raw_target in _FRAMESET_TARGETS else raw_target
    return obj


def _handle_object_block(
    block_type: str, p: dict[str, str], raw_id: str
) -> dict[str, object] | None:
    if p.get("view_type") == "line":
        return _handle_view_type_line(p, raw_id)
    if block_type == "line":
        return _handle_line_block(p, raw_id)
    if block_type == "shape":
        return _handle_shape(p, raw_id)
    if block_type == "textbox":
        return _handle_textbox(p, raw_id)
    return _handle_monitor_block(block_type, p, raw_id)


def cfg_to_board(content: str, map_name: str) -> dict[str, object]:
    """Convert legacy .cfg text to an OrbVis board JSON dict."""
    board: dict[str, object] = {
        "name": map_name,
        "alias": map_name,
        "readonly": False,
        "connection_id": "live_1",
        "icon_size": 22,
        "rotation_interval": 0,
        "hover_template": None,
        "context_template": None,
        "background_image": None,
        # cfg-imports render with NagVis-classic top-left anchoring + flat look.
        "render_mode": "nagvis_classic",
        # NagVis' global default z is 10 for every object type and is never
        # written per-object; objects without an explicit z inherit this.
        "default_z": 10,
        # NagVis falls back to a white canvas when map_image is missing.
        "background_color": "#ffffff",
        "view": {"type": "static"},
        "objects": [],
    }
    objects: list[dict[str, object]] = []
    counter = 0

    blocks = _parse_blocks(content)

    # Pre-pass: collect templates and global object-defaults. NagVis resolves
    # each parameter as object > template (``template=name``) > global > built-in
    # default; previously only the object's own value was seen, so lines that
    # inherited line_type from a template/global silently fell back to 11.
    templates: dict[str, dict[str, str]] = {}
    global_props: dict[str, str] = {}
    for block_type, p in blocks:
        if block_type == "template":
            name = p.get("name")
            if name:
                templates[name] = p
        elif block_type == "global":
            global_props = p
    global_defaults = {
        k: v
        for k, v in global_props.items()
        if k not in _NON_INHERITED_KEYS and k not in _GLOBAL_BOARD_KEYS
    }

    for block_type, p in blocks:
        if block_type == "global":
            _apply_global(board, p)
            continue
        if block_type not in _BLOCK_TYPES:
            continue
        counter += 1
        # object_id identifies the object and is never inherited.
        raw_id = p.get("object_id", str(counter))
        tmpl = {
            k: v
            for k, v in templates.get(p.get("template", ""), {}).items()
            if k not in _NON_INHERITED_KEYS
        }
        effective = {**global_defaults, **tmpl, **p}
        effective.pop("template", None)
        obj = _handle_object_block(block_type, effective, raw_id)
        if obj is not None:
            objects.append(obj)

    _resolve_pending_refs(objects)

    view = board.get("view")
    if isinstance(view, dict) and view.get("type") == "flow":
        objects = []
    board["objects"] = objects
    return board
