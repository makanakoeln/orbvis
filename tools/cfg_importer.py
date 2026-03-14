#!/usr/bin/env python3
"""
NagVis .cfg to JSON importer.

Parses legacy NagVis 1.x map configuration files and converts them
to the OrbVis JSON format.

Usage:
    python cfg_importer.py <input.cfg> [<output_dir>]
    python cfg_importer.py --batch <maps_dir> <output_dir>

Supports:
    - define global { ... }
    - define host/service/hostgroup/servicegroup/map/shape/line/textbox { ... }
    - Coordinate parsing (absolute integers and relative "100%50" references)
    - Label styling: label_x, label_y, label_size, label_color, label_background
    - Link fields: url, url_target
    - Textbox content: text field
    - Batch import of entire etc/maps/ directories
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
# Parser
# ---------------------------------------------------------------------------

@dataclass
class CfgBlock:
    block_type: str
    properties: dict[str, str] = field(default_factory=dict)


def parse_cfg_file(path: Path) -> list[CfgBlock]:
    """Parse a NagVis .cfg file into a list of blocks."""
    text = path.read_text(encoding="utf-8", errors="replace")
    blocks: list[CfgBlock] = []

    # Remove comments: # only at start of line or after whitespace (not inside values like #rrggbb)
    text = re.sub(r"(?m)^\s*#[^\n]*", "", text)
    text = re.sub(r"\s+#[^\n]*", "", text)
    text = re.sub(r";[^\n]*", "", text)

    # Match: define <type> { ... }
    pattern = re.compile(
        r"define\s+(\w+)\s*\{([^}]*)\}", re.DOTALL
    )

    for match in pattern.finditer(text):
        block_type = match.group(1).strip().lower()
        body = match.group(2)

        props: dict[str, str] = {}
        for line in body.splitlines():
            line = line.strip()
            if not line:
                continue
            # key=value or key = value
            kv = re.match(r"(\w+)\s*=\s*(.*)", line)
            if kv:
                props[kv.group(1).strip()] = kv.group(2).strip()

        blocks.append(CfgBlock(block_type=block_type, properties=props))

    return blocks


# ---------------------------------------------------------------------------
# Converter
# ---------------------------------------------------------------------------

def _parse_int(value: str, default: int = 0) -> int:
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def _parse_coord(value: str) -> tuple[int, str | None]:
    """Parse a NagVis coordinate value.

    Returns (resolved_int, original_string_or_None).
    Absolute integers are returned as-is with no original string.
    Relative references like "100%50" (offset +50 from object 100) are stored
    in extra for reference; the numeric offset is used as the resolved value.
    """
    v = value.strip()
    if v.lstrip("-").isdigit():
        return int(v), None
    # Relative format: <ref_id>%<offset>  e.g. "123%-10"
    m = re.match(r"(-?\d+)%(-?\d+)", v)
    if m:
        return int(m.group(2)), v  # use offset as best-effort position
    return 0, v


def _parse_bool(value: str, default: bool = False) -> bool:
    return value.lower() in ("1", "true", "yes") if value else default


def blocks_to_map_json(blocks: list[CfgBlock], map_name: str) -> dict:
    """Convert parsed blocks into the Orbvis map JSON structure."""
    globals_props: dict[str, Any] = {
        "alias": map_name,
        "background_image": None,
        "icon_size": 30,
        "backend_id": "live_1",
    }
    objects: list[dict] = []
    obj_counter = 0

    for block in blocks:
        p = block.properties

        if block.block_type == "global":
            if "alias" in p:
                globals_props["alias"] = p["alias"]
            if "map_image" in p:
                globals_props["background_image"] = p["map_image"]
            if "iconset" in p:
                pass  # iconset not directly mapped
            if "backend_id" in p:
                globals_props["backend_id"] = p["backend_id"]
            continue

        # Object types
        obj_type = block.block_type
        if obj_type not in ("host", "service", "hostgroup", "servicegroup", "map", "shape", "line", "textbox"):
            continue

        obj_counter += 1
        obj_id = p.get("object_id", str(obj_counter))

        # Parse coordinates (absolute integers or relative "ref%offset" format)
        x, x_orig = _parse_coord(p.get("x", "0"))
        y, y_orig = _parse_coord(p.get("y", "0"))

        obj: dict[str, Any] = {
            "id": obj_id,
            "type": obj_type,
            "x": x,
            "y": y,
            "view_type": p.get("view_type", "icon"),
            "label_show": _parse_bool(p.get("label_show", "1"), True),
            "extra": {},
        }

        # Preserve original relative coordinate strings for reference
        if x_orig is not None:
            obj["extra"]["x_orig"] = x_orig
        if y_orig is not None:
            obj["extra"]["y_orig"] = y_orig

        # Type-specific fields
        if obj_type == "host":
            obj["host_name"] = p.get("host_name")
        elif obj_type == "service":
            obj["host_name"] = p.get("host_name")
            obj["service_description"] = p.get("service_description")
        elif obj_type in ("hostgroup", "servicegroup"):
            obj["group_name"] = p.get("hostgroup_name") or p.get("servicegroup_name")
        elif obj_type == "map":
            obj["map_name"] = p.get("map_name")
        elif obj_type == "shape":
            obj["icon"] = p.get("icon")
        elif obj_type == "line":
            x2, x2_orig = _parse_coord(p.get("x2", "0"))
            y2, y2_orig = _parse_coord(p.get("y2", "0"))
            obj["extra"]["x2"] = x2
            obj["extra"]["y2"] = y2
            if x2_orig is not None:
                obj["extra"]["x2_orig"] = x2_orig
            if y2_orig is not None:
                obj["extra"]["y2_orig"] = y2_orig
            obj["line_type"] = _parse_int(p.get("line_type", "10"))

        if "label_text" in p:
            obj["label_text"] = p["label_text"]

        # Label styling
        if "label_x" in p:
            obj["label_x"] = _parse_int(p["label_x"])
        if "label_y" in p:
            obj["label_y"] = _parse_int(p["label_y"])
        if "label_size" in p:
            obj["label_size"] = _parse_int(p["label_size"], 11)
        if "label_color" in p:
            obj["label_color"] = p["label_color"]
        if "label_background" in p:
            obj["label_background"] = p["label_background"]

        # Link fields
        if "url" in p:
            obj["url"] = p["url"]
        if "url_target" in p:
            obj["url_target"] = p["url_target"]

        # Textbox content
        if obj_type == "textbox" and "text" in p:
            obj["label_text"] = p["text"]

        # Carry over any unknown properties
        known_keys = {
            "object_id", "x", "y", "x2", "y2", "view_type", "label_show", "label_text",
            "label_x", "label_y", "label_size", "label_color", "label_background",
            "url", "url_target", "text",
            "host_name", "service_description", "hostgroup_name", "servicegroup_name",
            "map_name", "icon", "line_type", "backend_id", "iconset",
        }
        for key, value in p.items():
            if key not in known_keys:
                obj["extra"][key] = value

        objects.append(obj)

    return {
        "name": map_name,
        "globals": globals_props,
        "objects": objects,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def convert_file(cfg_path: Path, output_dir: Path) -> Path:
    map_name = cfg_path.stem
    blocks = parse_cfg_file(cfg_path)
    map_json = blocks_to_map_json(blocks, map_name)

    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"{map_name}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(map_json, f, indent=2, ensure_ascii=False)

    print(f"✓  {cfg_path.name}  →  {out_path}  ({len(map_json['objects'])} objects)")
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Import NagVis 1.x .cfg maps to JSON")
    parser.add_argument("input", help=".cfg file or maps directory (with --batch)")
    parser.add_argument("output", nargs="?", default="./maps", help="Output directory (default: ./maps)")
    parser.add_argument("--batch", action="store_true", help="Import all .cfg files in a directory")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_dir = Path(args.output)

    if args.batch:
        if not input_path.is_dir():
            print(f"Error: {input_path} is not a directory", file=sys.stderr)
            sys.exit(1)
        cfg_files = list(input_path.glob("*.cfg"))
        if not cfg_files:
            print(f"No .cfg files found in {input_path}")
            return
        print(f"Importing {len(cfg_files)} map(s) from {input_path}…")
        for cfg_file in sorted(cfg_files):
            convert_file(cfg_file, output_dir)
    else:
        if not input_path.is_file():
            print(f"Error: {input_path} is not a file", file=sys.stderr)
            sys.exit(1)
        convert_file(input_path, output_dir)

    print(f"\nDone. Maps written to: {output_dir}")


if __name__ == "__main__":
    main()
