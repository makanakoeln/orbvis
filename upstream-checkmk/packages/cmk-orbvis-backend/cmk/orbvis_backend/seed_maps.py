#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Copy bundled demo maps into MAPS_DIR on first start, gated by a marker.

After the marker is set, subsequent starts refresh demo-* maps (and their
backgrounds) only if the file already exists in maps_dir. That keeps user-
deleted demo maps deleted while still letting shipped demo content evolve
with software updates.
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)

SEED_DIR = Path(__file__).parent / "_seed_maps"
MARKER_NAME = ".demo-seeded"
DEMO_PREFIX = "demo-"


def _refresh_existing_demo_files(maps_dir: Path) -> int:
    """Overwrite demo-* json/background files that already exist in maps_dir."""
    refreshed = 0
    for src in SEED_DIR.glob(f"{DEMO_PREFIX}*.json"):
        dst = maps_dir / src.name
        if dst.exists():
            shutil.copy2(src, dst)
            refreshed += 1

    bg_src_dir = SEED_DIR / "backgrounds"
    bg_dst_dir = maps_dir / "backgrounds"
    if bg_src_dir.is_dir() and bg_dst_dir.is_dir():
        for src in bg_src_dir.iterdir():
            if src.is_file():
                dst = bg_dst_dir / src.name
                if dst.exists():
                    shutil.copy2(src, dst)
    return refreshed


def seed_demo_maps(maps_dir: Path) -> None:
    marker = maps_dir / MARKER_NAME
    maps_dir.mkdir(parents=True, exist_ok=True)

    # Marker present: refresh demos that still exist; deleted demos stay gone.
    if marker.exists():
        refreshed = _refresh_existing_demo_files(maps_dir)
        if refreshed:
            logger.info("Refreshed %d built-in demo map(s).", refreshed)
        return

    # Pre-existing install with user maps: claim seeded so demo deletions
    # stick across future restarts.
    if any(maps_dir.glob("*.json")):
        marker.touch()
        logger.info("Demo seed skipped: maps directory already populated.")
        return

    copied = 0
    for src in SEED_DIR.glob("*.json"):
        shutil.copy2(src, maps_dir / src.name)
        copied += 1

    bg_src = SEED_DIR / "backgrounds"
    if bg_src.is_dir():
        bg_dst = maps_dir / "backgrounds"
        bg_dst.mkdir(parents=True, exist_ok=True)
        for src in bg_src.iterdir():
            if src.is_file():
                shutil.copy2(src, bg_dst / src.name)

    marker.touch()
    logger.info("Seeded %d built-in demo map(s).", copied)
