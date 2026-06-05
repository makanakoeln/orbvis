#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Discover the OrbVis boards stored on the local site"""

import json
from pathlib import Path
from typing import NamedTuple

import cmk.utils.paths


class BoardSummary(NamedTuple):
    name: str
    alias: str


def boards_dir() -> Path:
    return cmk.utils.paths.omd_root / "var" / "orbvis" / "boards"


def load_board_summaries() -> list[BoardSummary]:
    directory = boards_dir()
    if not directory.is_dir():
        return []
    return [
        _load_board_summary(path)
        for path in sorted(directory.glob("*.json"))
        if not _is_demo_board(path.stem)
    ]


def _is_demo_board(stem: str) -> bool:
    return stem == "demo" or stem.startswith("demo-")


def _load_board_summary(path: Path) -> BoardSummary:
    try:
        data = json.loads(path.read_text())
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return BoardSummary(name=path.stem, alias=path.stem)
    if not isinstance(data, dict):
        return BoardSummary(name=path.stem, alias=path.stem)
    name = str(data.get("name") or path.stem)
    alias = str(data.get("alias") or name)
    return BoardSummary(name=name, alias=alias)
