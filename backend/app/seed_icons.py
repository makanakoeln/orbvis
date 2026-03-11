"""Seed the user-facing icons directory with built-in icons on startup.

Built-in icons (Tabler Icons, MIT licence) are shipped with the package in
``builtin_icons/``.  They are copied once into the writable icons directory
so that a fresh install already has a usable icon set.  Existing files are
never overwritten, so user customisations and deletions are preserved.
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)

_BUILTIN_DIR = Path(__file__).parent / "builtin_icons"
_ICON_SUFFIXES = {".svg", ".png", ".jpg", ".jpeg", ".webp"}


def seed_builtin_icons(icons_dir: Path) -> None:
    """Copy missing built-in icons into *icons_dir* (non-destructively)."""
    if not _BUILTIN_DIR.is_dir():
        return

    icons_dir.mkdir(parents=True, exist_ok=True)
    seeded = 0

    for src in sorted(_BUILTIN_DIR.iterdir()):
        if src.is_file() and src.suffix.lower() in _ICON_SUFFIXES:
            dst = icons_dir / src.name
            if not dst.exists():
                shutil.copy2(src, dst)
                seeded += 1

    if seeded:
        logger.info("Seeded %d built-in icon(s) into %s", seeded, icons_dir)
