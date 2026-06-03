#!/usr/bin/env python3
"""
Legacy .cfg to OrbVis JSON importer.

Parses legacy map configuration files and converts them
to the OrbVis v2 board JSON format.

Usage:
    python cfg_importer.py <input.cfg> [<output_dir>]
    python cfg_importer.py --batch <maps_dir> <output_dir>
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Legacy line_type integers from the .cfg map format. 13/14/15 only appear on
# stateful lines (service block with view_type=line); 20 is not a valid value.
# ---------------------------------------------------------------------------
LINE_TYPE_MAP: dict[int, dict[str, Any]] = {
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

# Rough icon_size from legacy iconset name
ICONSET_SIZE: dict[str, int] = {
    "std_big": 30,
    "std_medium": 24,
    "std": 22,
    "std_small": 16,
}

# Stock legacy gadget URL → OrbVis gadget_type.
# Custom/unknown gadget_urls fall back to icon mode with a warning.
GADGET_URL_MAP: dict[str, str] = {
    "std_speedometer.php": "gauge",
    "std_speedometer2.php": "gauge",
    "std_bar.php": "bar",
    "std_html_bar.php": "bar",
}

# Legacy url_target values that reference the old CMK frameset — remap to _blank
_FRAMESET_TARGETS = {"main", "frames", "main_window"}


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


@dataclass
class CfgBlock:
    block_type: str
    properties: dict[str, str] = field(default_factory=dict)


def parse_cfg_file(path: Path) -> list[CfgBlock]:
    """Parse a legacy .cfg file into a list of define blocks."""
    text = path.read_text(encoding="utf-8", errors="replace")

    # Strip line comments (but NOT inline # inside colour values like #rrggbb).
    # Rule: a standalone # at the start of a line is a comment; semicolons too.
    text = re.sub(r"(?m)^\s*#[^\n]*", "", text)
    text = re.sub(r"(?m)^\s*;[^\n]*", "", text)

    blocks: list[CfgBlock] = []
    pattern = re.compile(r"define\s+(\w+)\s*\{([^}]*)\}", re.DOTALL)

    for match in pattern.finditer(text):
        block_type = match.group(1).strip().lower()
        body = match.group(2)

        props: dict[str, str] = {}
        for line in body.splitlines():
            line = line.strip()
            if not line:
                continue
            kv = re.match(r"(\w+)\s*=\s*(.*)", line)
            if kv:
                props[kv.group(1).strip()] = kv.group(2).strip()

        blocks.append(CfgBlock(block_type=block_type, properties=props))

    return blocks


# ---------------------------------------------------------------------------
# Conversion helpers
# ---------------------------------------------------------------------------


def _int(value: str | None, default: int = 0) -> int:
    try:
        return int(value)  # type: ignore[arg-type]
    except (ValueError, TypeError):
        return default


def _bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes")


@dataclass
class Coord:
    """A NagVis-style coordinate.

    - Absolute: ``value`` set, ``ref`` is ``None``.
    - Relative: ``ref`` holds the referenced object_id, ``offset`` the additive
      offset; ``value`` is a best-effort fallback (just the offset) used when
      the referenced object cannot be resolved during the second pass.
    """

    value: int
    ref: str | None = None
    offset: int | None = None


# NagVis object_ids are hex-ish strings (e.g. ``5148ed``); accept any
# alphanumeric+underscore identifier so external imports also resolve.
_REL_COORD_RE = re.compile(r"^([A-Za-z0-9_]+)%([+-]?\d+)$")


def _parse_coord(value: str) -> Coord:
    """Parse one legacy coordinate value.

    Legacy absolute ``"123"``       → ``Coord(123)``
    Legacy relative ``"5148ed%10"`` → ``Coord(value=10, ref='5148ed', offset=10)``
    Anything else falls back to ``Coord(0)``.
    """
    v = value.strip()
    if v.lstrip("-").isdigit():
        return Coord(int(v))
    m = _REL_COORD_RE.match(v)
    if m:
        return Coord(value=int(m.group(2)), ref=m.group(1), offset=int(m.group(2)))
    return Coord(0)


def _parse_axis_coords(raw: str, fallback_second: str) -> tuple[Coord, Coord, Coord | None]:
    """Parse one axis of a legacy line into (start, end, optional bend).

    Legacy encodes a line's coords as a comma-separated list per axis:
        x=x1,x2        two endpoints
        x=x1,x2,x3     NagVis two-segment line: x2 is the bend/meeting point

    First and last values are the endpoints; the middle value (when ≥3 are
    present) is the bend. NagVis itself only reads index 1 as the mid and the
    last as the end, so anything between collapses to a single bend. Falls back
    to a separate ``x2``/``y2`` key when no comma is present.
    """
    if "," in raw:
        parts = [s.strip() for s in raw.split(",")]
        start = _parse_coord(parts[0])
        end = _parse_coord(parts[-1])
        mid = _parse_coord(parts[1]) if len(parts) >= 3 else None
        return start, end, mid
    return _parse_coord(raw), _parse_coord(fallback_second), None


def _parse_line_coords(
    p: dict[str, str],
) -> tuple[Coord, Coord, Coord, Coord, Coord | None, Coord | None]:
    """Parse legacy line coords into (x, y, x2, y2, mid_x, mid_y)."""
    x, x2, mid_x = _parse_axis_coords(p.get("x", "0"), p.get("x2", "0"))
    y, y2, mid_y = _parse_axis_coords(p.get("y", "0"), p.get("y2", "0"))
    return x, y, x2, y2, mid_x, mid_y


def _auto_size(value: str | None) -> int | None:
    """Return numeric textbox width/height, or ``None`` for legacy ``"auto"``."""
    if value is None:
        return None
    v = value.strip().lower()
    if v in {"auto", ""}:
        return None
    try:
        return int(v)
    except ValueError:
        return None


# NagVis label_style is a CSS-ish string ("color:#fff;font-size:14px;font-weight:bold").
# We extract the few properties OrbVis renders from a structured LabelConfig.
_STYLE_PX = re.compile(r"^(\d+(?:\.\d+)?)\s*(?:px)?$")


def _parse_label_style(raw: str | None) -> dict[str, Any]:
    """Extract OrbVis-relevant fields from a NagVis ``label_style`` value."""
    out: dict[str, Any] = {}
    if not raw:
        return out
    for decl in raw.split(";"):
        if ":" not in decl:
            continue
        key, val = decl.split(":", 1)
        key = key.strip().lower()
        val = val.strip()
        if not val:
            continue
        if key == "color":
            out["color"] = val
        elif key == "background-color":
            out["background"] = val
        elif key == "font-size":
            m = _STYLE_PX.match(val)
            if m:
                out["size"] = int(float(m.group(1)))
        elif key == "font-weight":
            out["weight"] = val
    return out


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


def _extract_html_style(html: str) -> dict[str, Any]:
    """Pull color/font-size/weight/text-align from inline HTML in a textbox."""
    out: dict[str, Any] = {}
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


def _color_or_default(value: str | None, default: str | None) -> str | None:
    """Normalise a colour value: empty/whitespace → ``default``."""
    if value is None:
        return default
    v = value.strip()
    return v if v else default


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


def _label_y(raw: str | None) -> int:
    """Parse legacy ``label_y``.

    NagVis default ``bottom`` puts the label top at ``object_y + icon_height``
    (22 for the default iconset). Numeric values stay as pixel offsets.
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


def _label(p: dict[str, str], *, show_default: bool = True) -> dict[str, Any]:
    """Build a LabelConfig dict from legacy properties.

    NagVis encodes typography via the free-form ``label_style`` CSS string.
    Explicit ``label_color`` / ``label_background`` keys win when present;
    otherwise we recover values from the style string.
    """
    style = _parse_label_style(p.get("label_style"))
    raw_bg = p.get("label_background") or style.get("background")
    # NagVis canvas is light, so default to black; flip only for opaque-dark bg.
    default_color = "#ffffff" if _bg_is_opaque_dark(raw_bg) else "#000000"
    return {
        "show": _bool(p.get("label_show"), show_default),
        "text": _label_text(p.get("label_text")),
        "x": _label_x(p.get("label_x")),
        "y": _label_y(p.get("label_y")),
        "size": _int(p.get("label_size"), style.get("size", 11)),
        "color": p.get("label_color") or style.get("color", default_color),
        "background": raw_bg or "transparent",
        "width": _int(p.get("label_width")) or None,
    }


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


def _set_explicit_z(obj: dict[str, Any], p: dict[str, str]) -> None:
    """Write ``z`` only when the cfg block set it explicitly.

    NagVis stores no z on objects that use its global default (10); leaving z
    unset here lets such objects inherit the board's ``default_z`` instead of
    each type inventing its own layer — reproducing NagVis layering 1:1.
    """
    if "z" in p:
        obj["z"] = _int(p["z"])


def _attach_pending_refs(obj: dict[str, Any], **coords: Coord) -> None:
    """Stash relative-coord references on the object for the resolution pass."""
    refs = {key: c for key, c in coords.items() if c.ref is not None}
    if refs:
        obj["_pending_refs"] = {
            key: {"ref": c.ref, "offset": c.offset or 0} for key, c in refs.items()
        }


def _display(p: dict[str, str]) -> tuple[dict[str, Any], str | None]:
    """Build a DisplayConfig dict from legacy properties.

    Returns ``(display_dict, warning)``. ``warning`` is non-None when a
    ``view_type=gadget`` was encountered with a ``gadget_url`` that has no
    OrbVis equivalent — the caller emits the message so it includes the
    object identifier.
    """
    mode = p.get("view_type", "icon")
    if mode not in ("icon", "text", "gadget"):
        mode = "icon"

    if mode != "gadget":
        return {"mode": mode}, None

    gadget_url = p.get("gadget_url", "").strip()
    gadget_type = GADGET_URL_MAP.get(gadget_url)

    if gadget_type is None:
        return {"mode": "icon"}, f"unknown gadget_url={gadget_url!r}, falling back to icon"

    # Stock legacy gadgets do not carry an explicit metric name; OrbVis
    # picks the service's first perfdata when gadget_metric is None.
    return {"mode": "gadget", "gadget_type": gadget_type, "gadget_metric": None}, None


def _url_target(raw: str | None) -> str:
    if raw and raw in _FRAMESET_TARGETS:
        return "_blank"
    return raw or "_blank"


# ---------------------------------------------------------------------------
# Main converter
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


def _apply_global(board: dict[str, Any], p: dict[str, str]) -> None:
    if "alias" in p:
        board["alias"] = p["alias"]
    if "map_image" in p:
        board["background_image"] = p["map_image"]
    if "background_color" in p:
        bg = _color_or_default(p["background_color"], None)
        if bg is not None:
            board["background_color"] = bg
    # NagVis cfg uses ``backend_id`` on disk; accept either spelling.
    if "backend_id" in p:
        board["connection_id"] = p["backend_id"]
    if "connection_id" in p:
        board["connection_id"] = p["connection_id"]
    if "iconset" in p:
        board["icon_size"] = ICONSET_SIZE.get(p["iconset"], 22)

    sources = {s.strip().lower() for s in p.get("sources", "").split(",") if s.strip()}
    if "automap" in sources:
        view: dict[str, Any] = {"type": "flow"}
        if p.get("root"):
            view["root"] = p["root"]
        if "child_layers" in p:
            view["child_layers"] = _int(p["child_layers"], -1)
        if "parent_layers" in p:
            view["parent_layers"] = _int(p["parent_layers"], 0)
        board["view"] = view
    elif sources & {"geomap", "dynmap", "worldmap"}:
        unsupported = sorted(sources & {"geomap", "dynmap", "worldmap"})
        print(
            f"  ⚠  source {','.join(unsupported)} not yet supported — board will be empty",
            file=sys.stderr,
        )


def _line_obj_common(p: dict[str, str], raw_id: str) -> dict[str, Any]:
    x, y, x2, y2, mid_x, mid_y = _parse_line_coords(p)
    line_type = _int(p.get("line_type", "11"))
    type_attrs = LINE_TYPE_MAP.get(line_type, _DEFAULT_LINE_TYPE)
    # NagVis lines may carry a label (``label_show=1`` + ``label_text``); fall
    # back to hidden when neither is present so the line stays a plain line.
    has_label = _bool(p.get("label_show")) or bool(p.get("label_text"))
    label = _label(p, show_default=has_label)
    obj: dict[str, Any] = {
        "id": f"line_{raw_id}",
        "type": "line",
        "x": x.value,
        "y": y.value,
        "x2": x2.value,
        "y2": y2.value,
        "label": label,
        # NagVis default line_color_border = #000000; outline renders behind
        # the colored fill.
        "line_color_border": _color_or_default(p.get("line_color_border"), "#000000"),
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
    _attach_pending_refs(obj, **refs)
    # NagVis line_width is the polygon half-width (-w to +w); OrbVis renders
    # it as full stroke width. Double on import.
    obj["line_width"] = _int(p.get("line_width"), 3) * 2
    return obj


def _handle_view_type_line(p: dict[str, str], raw_id: str) -> dict[str, Any]:
    obj = _line_obj_common(p, raw_id)
    if "host_name" in p:
        obj["host_name"] = p["host_name"]
    if "service_description" in p:
        obj["service_description"] = p["service_description"]
    if "line_label_in" in p:
        obj["weathermap_metric"] = p["line_label_in"]
    if "line_label_out" in p:
        obj["weathermap_metric_out"] = p["line_label_out"]
    return obj


def _handle_line_block(p: dict[str, str], raw_id: str) -> dict[str, Any]:
    obj = _line_obj_common(p, raw_id)
    # Stateful line variants (13/14/15) may reference a service so the
    # bandwidth labels and gradient have data to read from.
    if obj.get("line_perfdata_label") not in (None, "none"):
        if "host_name" in p:
            obj["host_name"] = p["host_name"]
        if "service_description" in p:
            obj["service_description"] = p["service_description"]
        if "weathermap_metric" in p:
            obj["weathermap_metric"] = p["weathermap_metric"]
    return obj


def _handle_shape(p: dict[str, str], raw_id: str) -> dict[str, Any]:
    x = _parse_coord(p.get("x", "0"))
    y = _parse_coord(p.get("y", "0"))
    obj: dict[str, Any] = {
        "id": f"image_{raw_id}",
        "type": "image",
        "x": x.value,
        "y": y.value,
        "image_src": p.get("icon") or None,
        "label": {"show": False},
    }
    _set_explicit_z(obj, p)
    _attach_pending_refs(obj, x=x, y=y)
    return obj


def _handle_textbox(p: dict[str, str], raw_id: str) -> dict[str, Any]:
    # nagvis_classic anchors top-left; keep raw NagVis coords for 1:1 layout.
    x = _parse_coord(p.get("x", "0"))
    y = _parse_coord(p.get("y", "0"))

    width = _auto_size(p.get("w"))
    height = _auto_size(p.get("h"))

    raw_text = p.get("text") or None
    html_style: dict[str, Any] = {}
    if raw_text:
        html_style = _extract_html_style(raw_text)
        raw_text = re.sub(r"<br\s*/?>", "\n", raw_text, flags=re.IGNORECASE)
        raw_text = re.sub(r"<[^>]+>", "", raw_text)
        raw_text = _decode_html_entities(raw_text)
    style = _parse_label_style(p.get("style"))
    label: dict[str, Any] = {
        "show": True,
        "text": raw_text,
        "x": 0,
        "y": 0,
        "size": html_style.get("size", style.get("size", 11)),
        "color": html_style.get("color", style.get("color", "#000000")),
        "background": _color_or_default(p.get("background_color"), "transparent"),
    }
    if "weight" in html_style:
        label["weight"] = html_style["weight"]
    if "align" in html_style:
        label["align"] = html_style["align"]
    obj: dict[str, Any] = {
        "id": f"textbox_{raw_id}",
        "type": "textbox",
        "x": x.value,
        "y": y.value,
        "label": label,
    }
    _set_explicit_z(obj, p)
    if width is not None:
        obj["textbox_width"] = width
    if height is not None:
        obj["textbox_height"] = height
    # NagVis textbox border_color default is #e5e5e5 (light gray); explicit
    # #000000 in cfg renders prominent black, unset stays subtle.
    obj["textbox_border"] = _color_or_default(p.get("border_color"), "#e5e5e5")
    # NagVis default background is transparent; lets lines drawn under the
    # textbox stay visible on the white canvas.
    obj["textbox_background"] = _color_or_default(p.get("background_color"), "transparent")
    _attach_pending_refs(obj, x=x, y=y)
    return obj


def _apply_object_backend(obj: dict[str, Any], p: dict[str, str]) -> None:
    """Mirror NagVis' per-object ``backend_id`` onto OrbVis' ``connection_id``.

    NagVis lets a single map mix backends — this carries that intent into
    OrbVis where state_service routes the object to the matching connection.
    Boards' default ``backend_id`` is applied at the global block, so we only
    set the per-object override when the value differs.
    """
    bid = p.get("backend_id") or p.get("connection_id")
    if bid:
        obj["connection_id"] = bid


def _apply_type_specific(obj: dict[str, Any], legacy_type: str, p: dict[str, str]) -> None:
    if legacy_type == "host":
        obj["host_name"] = p.get("host_name")
        if _bool(p.get("only_hard_states")):
            obj["only_hard_states"] = True
        if _bool(p.get("recognize_services")):
            obj["recognize_services"] = True
    elif legacy_type == "service":
        obj["host_name"] = p.get("host_name")
        obj["service_description"] = p.get("service_description")
        if _bool(p.get("only_hard_states")):
            obj["only_hard_states"] = True
    elif legacy_type == "hostgroup":
        obj["group_name"] = p.get("hostgroup_name") or p.get("group_name")
    elif legacy_type == "servicegroup":
        obj["group_name"] = p.get("servicegroup_name") or p.get("group_name")
    elif legacy_type == "map":
        obj["map_name"] = p.get("map_name")
    elif legacy_type == "aggr":
        # Newer .cfg exports write 'name='; older CLI imports used 'aggr_name='.
        # Accept either form.
        obj["aggregation_id"] = p.get("aggr_name") or p.get("name")
        if "aggr_url" in p and "url" not in p:
            obj["url"] = p["aggr_url"]
    elif legacy_type == "dyngroup":
        ot = (p.get("object_types") or "host").strip().lower()
        obj["object_types"] = "service" if ot == "service" else "host"
        obj["object_filter"] = p.get("object_filter") or None


def _handle_monitor_block(legacy_type: str, p: dict[str, str], raw_id: str) -> dict[str, Any]:
    """host / service / hostgroup / servicegroup / map / aggr."""
    x = _parse_coord(p.get("x", "0"))
    y = _parse_coord(p.get("y", "0"))
    orbvis_type = "aggregation" if legacy_type == "aggr" else legacy_type
    display, warning = _display(p)
    if warning:
        print(f"  ⚠  {orbvis_type} {raw_id}: {warning}", file=sys.stderr)
    obj: dict[str, Any] = {
        "id": f"{orbvis_type}_{raw_id}",
        "type": orbvis_type,
        "x": x.value,
        "y": y.value,
        "label": _label(p),
        "display": display,
        # NagVis .box CSS draws every label with a 1px solid border (#e5e5e5).
        "label_border": (p.get("label_border") or "#e5e5e5").strip(),
    }
    _set_explicit_z(obj, p)
    _apply_type_specific(obj, legacy_type, p)
    _apply_object_backend(obj, p)
    if "url" in p:
        obj["url"] = p["url"]
    if "url_target" in p:
        obj["url_target"] = _url_target(p["url_target"])
    _attach_pending_refs(obj, x=x, y=y)
    return obj


def _handle_object_block(legacy_type: str, p: dict[str, str], raw_id: str) -> dict[str, Any]:
    if p.get("view_type") == "line" and legacy_type != "line":
        obj = _handle_view_type_line(p, raw_id)
    elif legacy_type == "line":
        obj = _handle_line_block(p, raw_id)
    elif legacy_type == "shape":
        obj = _handle_shape(p, raw_id)
    elif legacy_type == "textbox":
        obj = _handle_textbox(p, raw_id)
    else:
        # _handle_monitor_block already applies the backend override.
        return _handle_monitor_block(legacy_type, p, raw_id)
    _apply_object_backend(obj, p)
    return obj


def _resolve_pending_refs(objects: list[dict[str, Any]]) -> None:
    """Resolve ``_pending_refs`` on each object using the raw NagVis object_id index.

    Lines and other objects can reference another object via ``ref%offset``
    coords. We assume the raw NagVis object_id is the trailing component of
    each generated OrbVis id (``<type>_<raw_id>``), so we iterate until either
    nothing changes (transitive refs settled) or we hit a small fix-point cap.
    Unresolved refs silently fall back to the offset value already written.
    """
    by_raw: dict[str, dict[str, Any]] = {}
    for obj in objects:
        raw_id = str(obj.get("id", "")).split("_", 1)[-1]
        if raw_id:
            by_raw[raw_id] = obj

    # Multiple passes so chains (A → B → C) settle. Cap = 5 — NagVis itself
    # warns about cycles, so deep chains are rare.
    for _ in range(5):
        changed = False
        for obj in objects:
            refs = obj.get("_pending_refs")
            if not refs:
                continue
            for axis, ref in list(refs.items()):
                target = by_raw.get(ref["ref"])
                if target is None:
                    continue
                # x2/y2/mid_x reuse the target's x/y — NagVis only stores one
                # endpoint per object, lines reuse it by axis-name match.
                base_axis = "x" if axis in ("x", "x2", "mid_x") else "y"
                target_pending = target.get("_pending_refs") or {}
                if base_axis in target_pending:
                    continue
                obj[axis] = int(target.get(base_axis, 0)) + int(ref["offset"])
                refs.pop(axis)
                changed = True
            if not refs:
                obj.pop("_pending_refs", None)
        if not changed:
            break

    # Strip any unresolved refs so they don't leak into the JSON output.
    for obj in objects:
        obj.pop("_pending_refs", None)


def blocks_to_board_json(blocks: list[CfgBlock], map_name: str) -> dict[str, Any]:
    """Convert parsed legacy blocks into an OrbVis v2 board JSON dict."""
    board: dict[str, Any] = {
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
    objects: list[dict[str, Any]] = []
    counter = 0

    for block in blocks:
        p = block.properties
        if block.block_type == "global":
            _apply_global(board, p)
            continue
        if block.block_type not in _BLOCK_TYPES:
            continue
        counter += 1
        raw_id = p.get("object_id", str(counter))
        objects.append(_handle_object_block(block.block_type, p, raw_id))

    _resolve_pending_refs(objects)

    view = board.get("view")
    if isinstance(view, dict) and view.get("type") == "flow":
        objects = []
    board["objects"] = objects
    return board


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def convert_file(cfg_path: Path, output_dir: Path) -> Path:
    map_name = cfg_path.stem
    blocks = parse_cfg_file(cfg_path)
    board = blocks_to_board_json(blocks, map_name)

    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"{map_name}.json"
    out_path.write_text(json.dumps(board, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"✓  {cfg_path.name}  →  {out_path}  ({len(board['objects'])} objects)")
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Import legacy .cfg maps to OrbVis JSON")
    parser.add_argument("input", help=".cfg file or maps directory (with --batch)")
    parser.add_argument(
        "output", nargs="?", default="./maps", help="Output directory (default: ./maps)"
    )
    parser.add_argument("--batch", action="store_true", help="Import all .cfg files in a directory")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_dir = Path(args.output)

    if args.batch:
        if not input_path.is_dir():
            print(f"Error: {input_path} is not a directory", file=sys.stderr)
            sys.exit(1)
        cfg_files = sorted(input_path.glob("*.cfg"))
        if not cfg_files:
            print(f"No .cfg files found in {input_path}")
            return
        print(f"Importing {len(cfg_files)} map(s) from {input_path}…")
        for cfg_file in cfg_files:
            convert_file(cfg_file, output_dir)
    else:
        if not input_path.is_file():
            print(f"Error: {input_path} is not a file", file=sys.stderr)
            sys.exit(1)
        convert_file(input_path, output_dir)

    print(f"\nDone. Maps written to: {output_dir}")


if __name__ == "__main__":
    main()
