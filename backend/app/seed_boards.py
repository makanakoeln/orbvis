"""Copy bundled demo boards into BOARDS_DIR on first start, gated by a marker."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)

SEED_DIR = Path(__file__).parent / "_seed_boards"
MARKER_NAME = ".demo-seeded"


def seed_demo_boards(boards_dir: Path) -> None:
    marker = boards_dir / MARKER_NAME
    if marker.exists():
        return

    boards_dir.mkdir(parents=True, exist_ok=True)

    # Pre-existing install with user boards: claim seeded so the user's
    # demo deletions stick after future restarts.
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
