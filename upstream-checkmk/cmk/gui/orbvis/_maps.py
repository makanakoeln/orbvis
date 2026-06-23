#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Discover the Checkmk Maps stored on the local site"""

import json
from pathlib import Path
from typing import NamedTuple

import cmk.utils.paths


class MapSummary(NamedTuple):
    name: str
    alias: str


def maps_dir() -> Path:
    return cmk.utils.paths.omd_root / "var" / "orbvis" / "maps"


def load_map_summaries() -> list[MapSummary]:
    directory = maps_dir()
    if not directory.is_dir():
        return []
    return [
        _load_map_summary(path)
        for path in sorted(directory.glob("*.json"))
        if not _is_demo_map(path.stem)
    ]


def _is_demo_map(stem: str) -> bool:
    return stem == "demo" or stem.startswith("demo-")


def _load_map_summary(path: Path) -> MapSummary:
    try:
        data = json.loads(path.read_text())
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return MapSummary(name=path.stem, alias=path.stem)
    if not isinstance(data, dict):
        return MapSummary(name=path.stem, alias=path.stem)
    name = str(data.get("name") or path.stem)
    alias = str(data.get("alias") or name)
    return MapSummary(name=name, alias=alias)
