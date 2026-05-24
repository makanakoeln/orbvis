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


def _coord(v: str) -> int:
    v = v.strip()
    if v.lstrip("-").isdigit():
        return int(v)
    m = re.match(r"-?\d+%(-?\d+)", v)
    return int(m.group(1)) if m else 0


def _line_coords(p: dict[str, str]) -> tuple[int, int, int, int]:
    rx, ry = p.get("x", "0"), p.get("y", "0")
    if "," in rx:
        x1s, x2s = rx.split(",", 1)
        x, x2 = _coord(x1s), _coord(x2s)
    else:
        x, x2 = _coord(rx), _coord(p.get("x2", "0"))
    if "," in ry:
        y1s, y2s = ry.split(",", 1)
        y, y2 = _coord(y1s), _coord(y2s)
    else:
        y, y2 = _coord(ry), _coord(p.get("y2", "0"))
    return x, y, x2, y2


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


def _bg_is_opaque_light(value: str | None) -> bool:
    if not value:
        return False
    v = value.strip().lower()
    if v in {"transparent", ""}:
        return False
    if v.startswith("#") and len(v) in (4, 7):
        try:
            if len(v) == 4:
                r, g, b = (int(c * 2, 16) for c in v[1:])
            else:
                r, g, b = int(v[1:3], 16), int(v[3:5], 16), int(v[5:7], 16)
        except ValueError:
            return False
        return (r + g + b) / 3 > 180
    return False


def _label(p: dict[str, str], *, show_default: bool = True) -> dict[str, object]:
    raw_bg = p.get("label_background", "transparent")
    # OrbVis defaults to white text; flip to black on opaque light backgrounds
    # so imported NagVis labels don't disappear.
    default_color = "#000000" if _bg_is_opaque_light(raw_bg) else "#ffffff"
    return {
        "show": _bool(p.get("label_show"), show_default),
        "text": _label_text(p.get("label_text")),
        "x": _label_x(p.get("label_x")),
        "y": _int(p.get("label_y"), 34),
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
    x, y, x2, y2 = _line_coords(p)
    type_attrs = LINE_TYPE_MAP.get(_int(p.get("line_type", "11")), _DEFAULT_LINE_TYPE)
    obj: dict[str, object] = {
        "id": f"line_{raw_id}",
        "type": "line",
        "x": x,
        "y": y,
        "z": _int(p.get("z"), 1),
        "x2": x2,
        "y2": y2,
        "label": {"show": False},
        **type_attrs,
    }
    if "line_width" in p:
        obj["line_width"] = _int(p["line_width"])
    return obj


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
    return obj


def _handle_shape(p: dict[str, str], raw_id: str) -> dict[str, object]:
    return {
        "id": f"image_{raw_id}",
        "type": "image",
        "x": _coord(p.get("x", "0")),
        "y": _coord(p.get("y", "0")),
        "z": _int(p.get("z"), 1),
        "image_src": p.get("icon") or None,
        "label": {"show": False},
    }


def _handle_textbox(p: dict[str, str], raw_id: str) -> dict[str, object]:
    raw_text = p.get("text") or None
    inline_color: str | None = None
    if raw_text:
        # OrbVis strips HTML for XSS; pull the first inline color first so
        # dark text on a light imported background stays readable.
        m = re.search(
            r'(?:<font[^>]*color=["\']([^"\']+)|color\s*:\s*([^;"\']+))',
            raw_text,
            flags=re.IGNORECASE,
        )
        if m:
            inline_color = (m.group(1) or m.group(2) or "").strip() or None
        raw_text = re.sub(r"<br\s*/?>", "\n", raw_text, flags=re.IGNORECASE)
        raw_text = re.sub(r"<[^>]+>", "", raw_text)
    width = (
        _int(p.get("w"), 200) if (p.get("w") or "").strip().lower() not in {"auto", ""} else None
    )
    height = (
        _int(p.get("h"), 40) if (p.get("h") or "").strip().lower() not in {"auto", ""} else None
    )
    # legacy textbox x/y is top-left; OrbVis centers objects — offset by half w/h
    tx = _coord(p.get("x", "0")) + (width // 2 if width else 0)
    ty = _coord(p.get("y", "0")) + (height // 2 if height else 0)
    obj: dict[str, object] = {
        "id": f"textbox_{raw_id}",
        "type": "textbox",
        "x": tx,
        "y": ty,
        "z": _int(p.get("z"), 1),
        "label": {
            "show": True,
            "text": raw_text,
            "x": 0,
            "y": 0,
            "size": 11,
            "color": inline_color or "#000000",
            "background": "transparent",
        },
        # NagVis textbox default is opaque white; persist it so OrbVis doesn't
        # swap in its dark glass fallback.
        "textbox_background": (p.get("background_color") or "").strip() or "#FFFFFF",
    }
    if width is not None:
        obj["textbox_width"] = width
    if height is not None:
        obj["textbox_height"] = height
    border = (p.get("border_color") or "").strip()
    if border:
        obj["textbox_border"] = border
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
    obj: dict[str, object] = {
        "id": f"{orbvis_type}_{raw_id}",
        "type": orbvis_type,
        "x": _coord(p.get("x", "0")),
        "y": _coord(p.get("y", "0")),
        "z": _int(p.get("z"), 1),
        "label": _label(p),
        "display": _build_display(p),
    }
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
        "view": {"type": "static"},
        "objects": [],
    }
    objects: list[dict[str, object]] = []
    counter = 0

    for block_type, p in _parse_blocks(content):
        if block_type == "global":
            _apply_global(board, p)
            continue
        if block_type not in _BLOCK_TYPES:
            continue
        counter += 1
        raw_id = p.get("object_id", str(counter))
        obj = _handle_object_block(block_type, p, raw_id)
        if obj is not None:
            objects.append(obj)

    view = board.get("view")
    if isinstance(view, dict) and view.get("type") == "flow":
        objects = []
    board["objects"] = objects
    return board
