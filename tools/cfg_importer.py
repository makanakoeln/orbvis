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
_REL_COORD_RE = re.compile(r"^([A-Za-z0-9_]+)%(-?\d+)$")


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


def _parse_line_coords(p: dict[str, str]) -> tuple[Coord, Coord, Coord, Coord]:
    """Parse legacy line coords.

    Legacy format encodes both endpoints in x and y as comma-separated values:
        x=x1,x2   y=y1,y2

    Falls back to separate x2/y2 keys (non-standard but tolerated).
    """
    raw_x = p.get("x", "0")
    raw_y = p.get("y", "0")

    if "," in raw_x:
        x1_s, x2_s = raw_x.split(",", 1)
        x = _parse_coord(x1_s.strip())
        x2 = _parse_coord(x2_s.strip())
    else:
        x = _parse_coord(raw_x)
        x2 = _parse_coord(p.get("x2", "0"))

    if "," in raw_y:
        y1_s, y2_s = raw_y.split(",", 1)
        y = _parse_coord(y1_s.strip())
        y2 = _parse_coord(y2_s.strip())
    else:
        y = _parse_coord(raw_y)
        y2 = _parse_coord(p.get("y2", "0"))

    return x, y, x2, y2


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


def _color_or_default(value: str | None, default: str | None) -> str | None:
    """Normalise a colour value: empty/whitespace → ``default``."""
    if value is None:
        return default
    v = value.strip()
    return v if v else default


def _label(p: dict[str, str], *, show_default: bool = True) -> dict[str, Any]:
    """Build a LabelConfig dict from legacy properties.

    NagVis encodes typography via the free-form ``label_style`` CSS string.
    Explicit ``label_color`` / ``label_background`` keys win when present;
    otherwise we recover values from the style string.
    """
    style = _parse_label_style(p.get("label_style"))
    return {
        "show": _bool(p.get("label_show"), show_default),
        "text": p.get("label_text") or None,
        "x": _int(p.get("label_x")),
        "y": _int(p.get("label_y"), 34),
        "size": _int(p.get("label_size"), style.get("size", 11)),
        "color": p.get("label_color") or style.get("color", "#ffffff"),
        "background": p.get("label_background") or style.get("background", "transparent"),
    }


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
    {"host", "service", "hostgroup", "servicegroup", "map", "shape", "line", "textbox", "aggr"}
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
    x, y, x2, y2 = _parse_line_coords(p)
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
        # Lines have no NagVis default; sit below stateful objects (z=10) and
        # textboxes (z=5) by default so they don't cover hosts.
        "z": _int(p.get("z"), 0),
        "x2": x2.value,
        "y2": y2.value,
        "label": label,
        **type_attrs,
    }
    _attach_pending_refs(obj, x=x, y=y, x2=x2, y2=y2)
    if "line_width" in p:
        obj["line_width"] = _int(p["line_width"])
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
        # NagVis shape default z=1.
        "z": _int(p.get("z"), 1),
        "image_src": p.get("icon") or None,
        "label": {"show": False},
    }
    _attach_pending_refs(obj, x=x, y=y)
    return obj


def _handle_textbox(p: dict[str, str], raw_id: str) -> dict[str, Any]:
    # NagVis textbox x/y is top-left; OrbVis centers objects on x/y. We can
    # only translate when the size is numeric — for ``w=auto`` we fall back to
    # using the legacy top-left position as the OrbVis center.
    x = _parse_coord(p.get("x", "0"))
    y = _parse_coord(p.get("y", "0"))

    width = _auto_size(p.get("w"))
    height = _auto_size(p.get("h"))
    if width is not None:
        x.value += width // 2
    if height is not None:
        y.value += height // 2

    raw_text = p.get("text") or None
    if raw_text:
        raw_text = re.sub(r"<br\s*/?>", "\n", raw_text, flags=re.IGNORECASE)
        raw_text = re.sub(r"<[^>]+>", "", raw_text)
    style = _parse_label_style(p.get("style"))
    obj: dict[str, Any] = {
        "id": f"textbox_{raw_id}",
        "type": "textbox",
        "x": x.value,
        "y": y.value,
        # NagVis textbox default z=5.
        "z": _int(p.get("z"), 5),
        "label": {
            "show": True,
            "text": raw_text,
            "x": 0,
            "y": 0,
            "size": style.get("size", 11),
            "color": style.get("color", "#ffffff"),
            "background": _color_or_default(p.get("background_color"), "transparent"),
        },
    }
    if width is not None:
        obj["textbox_width"] = width
    if height is not None:
        obj["textbox_height"] = height
    border = _color_or_default(p.get("border_color"), None)
    if border is not None:
        obj["textbox_border"] = border
    bg = _color_or_default(p.get("background_color"), None)
    if bg is not None:
        obj["textbox_background"] = bg
    _attach_pending_refs(obj, x=x, y=y)
    return obj


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
        # NagVis default for stateful objects is z=10.
        "z": _int(p.get("z"), 10),
        "label": _label(p),
        "display": display,
    }
    _apply_type_specific(obj, legacy_type, p)
    if "url" in p:
        obj["url"] = p["url"]
    if "url_target" in p:
        obj["url_target"] = _url_target(p["url_target"])
    _attach_pending_refs(obj, x=x, y=y)
    return obj


def _handle_object_block(legacy_type: str, p: dict[str, str], raw_id: str) -> dict[str, Any]:
    if p.get("view_type") == "line" and legacy_type != "line":
        return _handle_view_type_line(p, raw_id)
    if legacy_type == "line":
        return _handle_line_block(p, raw_id)
    if legacy_type == "shape":
        return _handle_shape(p, raw_id)
    if legacy_type == "textbox":
        return _handle_textbox(p, raw_id)
    return _handle_monitor_block(legacy_type, p, raw_id)


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
                # x2/y2 reuse the target's x/y — NagVis only stores one
                # endpoint per object, lines reuse it by axis-name match.
                base_axis = "x" if axis in ("x", "x2") else "y"
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
