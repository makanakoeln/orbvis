"""Copy bundled demo boards into BOARDS_DIR on first start, gated by a marker.

After the marker is set, subsequent starts refresh demo-* boards (and their
backgrounds) only if the file already exists in boards_dir. That keeps user-
deleted demo boards deleted while still letting shipped demo content evolve
with software updates.
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)

SEED_DIR = Path(__file__).parent / "_seed_boards"
MARKER_NAME = ".demo-seeded"
DEMO_PREFIX = "demo-"


def _refresh_existing_demo_files(boards_dir: Path) -> int:
    """Overwrite demo-* json/background files that already exist in boards_dir."""
    refreshed = 0
    for src in SEED_DIR.glob(f"{DEMO_PREFIX}*.json"):
        dst = boards_dir / src.name
        if dst.exists():
            shutil.copy2(src, dst)
            refreshed += 1

    bg_src_dir = SEED_DIR / "backgrounds"
    bg_dst_dir = boards_dir / "backgrounds"
    if bg_src_dir.is_dir() and bg_dst_dir.is_dir():
        for src in bg_src_dir.iterdir():
            if src.is_file():
                dst = bg_dst_dir / src.name
                if dst.exists():
                    shutil.copy2(src, dst)
    return refreshed


def seed_demo_boards(boards_dir: Path) -> None:
    marker = boards_dir / MARKER_NAME
    boards_dir.mkdir(parents=True, exist_ok=True)

    # Marker present: refresh demos that still exist; deleted demos stay gone.
    if marker.exists():
        refreshed = _refresh_existing_demo_files(boards_dir)
        if refreshed:
            logger.info("Refreshed %d built-in demo board(s).", refreshed)
        return

    # Pre-existing install with user boards: claim seeded so demo deletions
    # stick across future restarts.
    if any(boards_dir.glob("*.json")):
        marker.touch()
        logger.info("Demo seed skipped: boards directory already populated.")
        return

    copied = 0
    for src in SEED_DIR.glob("*.json"):
        shutil.copy2(src, boards_dir / src.name)
        copied += 1

    bg_src = SEED_DIR / "backgrounds"
    if bg_src.is_dir():
        bg_dst = boards_dir / "backgrounds"
        bg_dst.mkdir(parents=True, exist_ok=True)
        for src in bg_src.iterdir():
            if src.is_file():
                shutil.copy2(src, bg_dst / src.name)

    marker.touch()
    logger.info("Seeded %d built-in demo board(s).", copied)
