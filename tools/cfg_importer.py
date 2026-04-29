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
# Legacy line_type integer → OrbVis line_style string
# ---------------------------------------------------------------------------
LINE_TYPE_MAP: dict[int, str] = {
    10: "plain",
    11: "arrow_end",
    12: "arrow_start",
    13: "arrow_both",
    14: "dashed",
    20: "weathermap",
}

# Rough icon_size from legacy iconset name
ICONSET_SIZE: dict[str, int] = {
    "std_big": 30,
    "std_medium": 24,
    "std": 22,
    "std_small": 16,
}

# NagVis stock gadget URL → OrbVis gadget_type
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


def _parse_coord(value: str) -> tuple[int, str | None]:
    """Return (resolved_int, original_if_relative).

    Legacy absolute coord  → int, None
    Legacy relative "ref%offset" → offset as int, original string
    """
    v = value.strip()
    if v.lstrip("-").isdigit():
        return int(v), None
    m = re.match(r"(-?\d+)%(-?\d+)", v)
    if m:
        return int(m.group(2)), v
    return 0, v


def _parse_line_coords(p: dict[str, str]) -> tuple[int, int, int, int]:
    """Parse legacy line coords.

    Legacy format encodes both endpoints in x and y as comma-separated values:
        x=x1,x2   y=y1,y2

    Falls back to separate x2/y2 keys (non-standard but tolerated).
    """
    raw_x = p.get("x", "0")
    raw_y = p.get("y", "0")

    if "," in raw_x:
        x1_s, x2_s = raw_x.split(",", 1)
        x, _ = _parse_coord(x1_s.strip())
        x2, _ = _parse_coord(x2_s.strip())
    else:
        x, _ = _parse_coord(raw_x)
        x2, _ = _parse_coord(p.get("x2", "0"))

    if "," in raw_y:
        y1_s, y2_s = raw_y.split(",", 1)
        y, _ = _parse_coord(y1_s.strip())
        y2, _ = _parse_coord(y2_s.strip())
    else:
        y, _ = _parse_coord(raw_y)
        y2, _ = _parse_coord(p.get("y2", "0"))

    return x, y, x2, y2


def _label(p: dict[str, str], *, show_default: bool = True) -> dict[str, Any]:
    """Build a LabelConfig dict from legacy properties."""
    return {
        "show": _bool(p.get("label_show"), show_default),
        "text": p.get("label_text") or None,
        "x": _int(p.get("label_x")),
        "y": _int(p.get("label_y"), 34),
        "size": _int(p.get("label_size"), 11),
        "color": p.get("label_color", "#ffffff"),
        "background": p.get("label_background", "transparent"),
    }


def _display(p: dict[str, str]) -> tuple[dict[str, Any], str | None]:
    """Build a DisplayConfig dict from legacy properties.

    Returns ``(display_dict, warning)``. ``warning`` is non-None when a NagVis
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

    # Standard NagVis gadgets do not carry an explicit metric name; OrbVis
    # picks the service's first perfdata when gadget_metric is None.
    return {"mode": "gadget", "gadget_type": gadget_type, "gadget_metric": None}, None


def _url_target(raw: str | None) -> str:
    if raw and raw in _FRAMESET_TARGETS:
        return "_blank"
    return raw or "_blank"


# ---------------------------------------------------------------------------
# Main converter
# ---------------------------------------------------------------------------


def blocks_to_board_json(blocks: list[CfgBlock], map_name: str) -> dict[str, Any]:
    """Convert parsed legacy blocks into an OrbVis v2 board JSON dict."""

    # Board-level defaults (populated from define global)
    board: dict[str, Any] = {
        "name": map_name,
        "alias": map_name,
        "readonly": False,
        "backend_id": "live_1",
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

        # ── global ──────────────────────────────────────────────────────────
        if block.block_type == "global":
            if "alias" in p:
                board["alias"] = p["alias"]
            if "map_image" in p:
                board["background_image"] = p["map_image"]
            if "backend_id" in p:
                board["backend_id"] = p["backend_id"]
            if "iconset" in p:
                board["icon_size"] = ICONSET_SIZE.get(p["iconset"], 22)
            continue

        # ── skip unknown block types ────────────────────────────────────────
        if block.block_type not in (
            "host",
            "service",
            "hostgroup",
            "servicegroup",
            "map",
            "shape",
            "line",
            "textbox",
            "aggr",
        ):
            continue

        counter += 1
        legacy_type = block.block_type
        raw_id = p.get("object_id", str(counter))

        # ── line ────────────────────────────────────────────────────────────
        if legacy_type == "line":
            x, y, x2, y2 = _parse_line_coords(p)
            line_type = _int(p.get("line_type", "10"))
            line_style = LINE_TYPE_MAP.get(line_type, "plain")

            obj: dict[str, Any] = {
                "id": f"line_{raw_id}",
                "type": "line",
                "x": x,
                "y": y,
                "z": _int(p.get("z"), 1),
                "x2": x2,
                "y2": y2,
                "line_style": line_style,
                "label": {"show": False},
            }
            # Weathermap lines may reference a service
            if line_style == "weathermap":
                if "host_name" in p:
                    obj["host_name"] = p["host_name"]
                if "service_description" in p:
                    obj["service_description"] = p["service_description"]
                if "weathermap_metric" in p:
                    obj["weathermap_metric"] = p["weathermap_metric"]
            objects.append(obj)
            continue

        # ── shape → image ───────────────────────────────────────────────────
        if legacy_type == "shape":
            x, _ = _parse_coord(p.get("x", "0"))
            y, _ = _parse_coord(p.get("y", "0"))
            objects.append(
                {
                    "id": f"image_{raw_id}",
                    "type": "image",
                    "x": x,
                    "y": y,
                    "z": _int(p.get("z"), 1),
                    "image_src": p.get("icon") or None,
                    "label": {"show": False},
                }
            )
            continue

        # ── textbox ─────────────────────────────────────────────────────────
        if legacy_type == "textbox":
            # legacy textbox x/y is top-left; OrbVis centers objects — offset by half w/h
            x, _ = _parse_coord(p.get("x", "0"))
            y, _ = _parse_coord(p.get("y", "0"))
            x += _int(p.get("w"), 200) // 2
            y += _int(p.get("h"), 40) // 2
            raw_text = p.get("text") or None
            if raw_text:
                raw_text = re.sub(r"<br\s*/?>", "\n", raw_text, flags=re.IGNORECASE)
                raw_text = re.sub(r"<[^>]+>", "", raw_text)
            objects.append(
                {
                    "id": f"textbox_{raw_id}",
                    "type": "textbox",
                    "x": x,
                    "y": y,
                    "z": _int(p.get("z"), 1),
                    "label": {
                        "show": True,
                        "text": raw_text,
                        "x": 0,
                        "y": 0,
                        "size": 11,
                        "color": "#ffffff",
                        "background": "transparent",
                    },
                }
            )
            continue

        # ── monitoring objects (host / service / hostgroup / servicegroup / map) ──
        x, _ = _parse_coord(p.get("x", "0"))
        y, _ = _parse_coord(p.get("y", "0"))

        orbvis_type = "aggregation" if legacy_type == "aggr" else legacy_type

        display, warning = _display(p)
        if warning:
            print(f"  ⚠  {orbvis_type} {raw_id}: {warning}", file=sys.stderr)

        obj = {
            "id": f"{orbvis_type}_{raw_id}",
            "type": orbvis_type,
            "x": x,
            "y": y,
            "z": _int(p.get("z"), 1),
            "label": _label(p),
            "display": display,
        }

        # Type-specific identity fields
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
            obj["aggregation_id"] = p.get("aggr_name")
            if "aggr_url" in p and "url" not in p:
                obj["url"] = p["aggr_url"]

        # Optional link
        if "url" in p:
            obj["url"] = p["url"]
        if "url_target" in p:
            obj["url_target"] = _url_target(p["url_target"])

        objects.append(obj)

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
