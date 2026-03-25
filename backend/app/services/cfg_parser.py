"""Parse NagVis .cfg map content and convert it to an OrbVis board dict.

Used by the import API endpoint; the standalone CLI (tools/cfg_importer.py)
contains its own copy of the same logic so it stays dependency-free.
"""

from __future__ import annotations

import re
from typing import Any

LINE_TYPE_MAP: dict[int, str] = {
    10: "plain",
    11: "arrow_end",
    12: "arrow_start",
    13: "arrow_both",
    14: "dashed",
    20: "weathermap",
}

ICONSET_SIZE: dict[str, int] = {
    "std_big": 30,
    "std_medium": 24,
    "std": 22,
    "std_small": 16,
}

_FRAMESET_TARGETS = {"main", "frames", "main_window"}


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


def _label(p: dict[str, str], *, show_default: bool = True) -> dict[str, Any]:
    return {
        "show": _bool(p.get("label_show"), show_default),
        "text": p.get("label_text") or None,
        "x": _int(p.get("label_x")),
        "y": _int(p.get("label_y"), 34),
        "size": _int(p.get("label_size"), 11),
        "color": p.get("label_color", "#ffffff"),
        "background": p.get("label_background", "transparent"),
    }


# ---------------------------------------------------------------------------
# Converter
# ---------------------------------------------------------------------------


def cfg_to_board(content: str, map_name: str) -> dict[str, Any]:
    """Convert NagVis .cfg text to an OrbVis board JSON dict."""
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

    for block_type, p in _parse_blocks(content):
        if block_type == "global":
            if "alias" in p:
                board["alias"] = p["alias"]
            if "map_image" in p:
                board["background_image"] = p["map_image"]
            if "backend_id" in p:
                board["backend_id"] = p["backend_id"]
            if "iconset" in p:
                board["icon_size"] = ICONSET_SIZE.get(p["iconset"], 22)
            continue

        if block_type not in (
            "host",
            "service",
            "hostgroup",
            "servicegroup",
            "map",
            "shape",
            "line",
            "textbox",
        ):
            continue

        counter += 1
        raw_id = p.get("object_id", str(counter))

        if block_type == "line":
            x, y, x2, y2 = _line_coords(p)
            line_style = LINE_TYPE_MAP.get(_int(p.get("line_type", "10")), "plain")
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
            if line_style == "weathermap":
                if "host_name" in p:
                    obj["host_name"] = p["host_name"]
                if "service_description" in p:
                    obj["service_description"] = p["service_description"]
            objects.append(obj)
            continue

        if block_type == "shape":
            objects.append(
                {
                    "id": f"image_{raw_id}",
                    "type": "image",
                    "x": _coord(p.get("x", "0")),
                    "y": _coord(p.get("y", "0")),
                    "z": _int(p.get("z"), 1),
                    "image_src": p.get("icon") or None,
                    "label": {"show": False},
                }
            )
            continue

        if block_type == "textbox":
            raw_text = p.get("text") or None
            if raw_text:
                raw_text = re.sub(r"<br\s*/?>", "\n", raw_text, flags=re.IGNORECASE)
                raw_text = re.sub(r"<[^>]+>", "", raw_text)
            # NagVis textbox x/y is top-left; OrbVis centers objects — offset by half w/h
            tx = _coord(p.get("x", "0")) + _int(p.get("w"), 200) // 2
            ty = _coord(p.get("y", "0")) + _int(p.get("h"), 40) // 2
            objects.append(
                {
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
                        "color": "#ffffff",
                        "background": "transparent",
                    },
                }
            )
            continue

        # host / service / hostgroup / servicegroup / map
        x = _coord(p.get("x", "0"))
        y = _coord(p.get("y", "0"))
        mode = p.get("view_type", "icon")
        if mode not in ("icon", "text", "gadget"):
            mode = "icon"
        obj = {
            "id": f"{block_type}_{raw_id}",
            "type": block_type,
            "x": x,
            "y": y,
            "z": _int(p.get("z"), 1),
            "label": _label(p),
            "display": {"mode": mode},
        }
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
        if "url" in p:
            obj["url"] = p["url"]
        if "url_target" in p:
            raw_target = p["url_target"]
            obj["url_target"] = "_blank" if raw_target in _FRAMESET_TARGETS else raw_target
        objects.append(obj)

    board["objects"] = objects
    return board
