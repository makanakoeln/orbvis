#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Seed the user-facing images directory with built-in images on startup.

Built-in images (Tabler Icons, MIT licence) are shipped with the package in
``builtin_icons/``.  They are copied once into the writable images directory
so that a fresh install already has a usable image set.  Existing files are
never overwritten, so user customisations and deletions are preserved.
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)

_BUILTIN_DIR = Path(__file__).parent / "builtin_icons"
_ICON_SUFFIXES = {".svg", ".png", ".jpg", ".jpeg", ".webp"}


def seed_builtin_images(images_dir: Path) -> None:
    """Copy missing built-in images into *images_dir* (non-destructively)."""
    if not _BUILTIN_DIR.is_dir():
        return

    images_dir.mkdir(parents=True, exist_ok=True)
    seeded = 0

    for src in sorted(_BUILTIN_DIR.iterdir()):
        if src.is_file() and src.suffix.lower() in _ICON_SUFFIXES:
            dst = images_dir / src.name
            if not dst.exists():
                shutil.copy2(src, dst)
                seeded += 1

    if seeded:
        logger.info("Seeded %d built-in image(s) into %s", seeded, images_dir)
