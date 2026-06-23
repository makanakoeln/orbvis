#!/usr/bin/env python3
"""Rename the OrbVis "board" domain term to "map" across a source tree.

This is the board->map half of the transform that produces the built-in
Checkmk variant ("Checkmk Maps"). It runs on the STAGED copy of the frontend
(and later the backend), never on the canonical frontend/src — the standalone
repo keeps "board" internally (API /boards, JSON keys, saved boards of the
2.3-2.5 deployments stay valid).

The rename is identifier-segment aware. Every English compound that embeds
"board" -- dashboard, keyboard, clipboard, checkerboard -- spells it lower
case after a letter, whereas every OrbVis identifier capitalises a fresh
camelCase segment (currentBoard, BoardObject) or starts the token on a
non-letter boundary (board_service, /boards, "boards"). So:

  * capital  ``Board`` is ALWAYS an OrbVis segment  -> rewrite unconditionally
    (no English word embeds a capital ``Board``).
  * lower    ``board`` is rewritten ONLY on a non-alnum left boundary, which
    excludes dash|key|clip|checker-board while keeping board / _board / /board.

A guard asserts the per-file count of the known collision words is unchanged;
any drift aborts the run instead of silently corrupting a build.

Usage:
  rename-board-to-map.py <dir> [<dir> ...] [--check]

  --check   dry-run: report what would change, exit 1 if anything would, do
            not touch the tree.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Ordered, case-sensitive token rules. Plurals and SCREAMING forms first so
# the singular rules cannot nibble a prefix off them.
#
# Boundary legend:
#   (?<![A-Za-z0-9])  left boundary is start / _ / / / quote / space / ( ...
#                     -> blocks dashboard, keyboard, clipboard (letter on left)
#   (?![a-z])         right side is not a lower-case continuation
#                     -> blocks "boarding"/"boarded"; allows BoardObject,
#                        board_service, /boards, end-of-token
# Capital Board/Boards carry NO left boundary: a fresh camelCase segment is
# routinely preceded by a lower-case letter (useBoardsStore, currentBoard) and
# no English word embeds a capital ``Board``. Lower-case and SCREAMING forms
# KEEP the left boundary so dashboard / keyboard / KEYBOARD stay intact.
_RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"Boards(?![a-z])"), "Maps"),
    (re.compile(r"Board(?![a-z])"), "Map"),
    (re.compile(r"(?<![A-Za-z0-9])BOARDS(?![A-Za-z0-9])"), "MAPS"),
    (re.compile(r"(?<![A-Za-z0-9])BOARD(?![A-Za-z0-9])"), "MAP"),
    (re.compile(r"(?<![A-Za-z0-9])boards(?![a-z])"), "maps"),
    (re.compile(r"(?<![A-Za-z0-9])board(?![a-z])"), "map"),
]

# Words that embed "board" and must NEVER change. Counted case-insensitively
# before and after; any delta aborts the run.
_COLLISION_WORDS = (
    "dashboard",
    "keyboard",
    "clipboard",
    "cardboard",
    "billboard",
    "storyboard",
    "surfboard",
    "motherboard",
    "cupboard",
    "outboard",
    "soundboard",
    "leaderboard",
    "scoreboard",
    "whiteboard",
    "blackboard",
    "switchboard",
    "chalkboard",
    "signboard",
    "baseboard",
    "washboard",
    "headboard",
    "sideboard",
    "springboard",
    "floorboard",
    "skateboard",
    "snowboard",
    "breadboard",
    "checkerboard",
    "paperboard",
    "overboard",
    "aboard",
    "seaboard",
)
_COLLISION_RE = re.compile("|".join(_COLLISION_WORDS), re.IGNORECASE)

# Only transform textual sources; leave binary assets (png/svg-as-binary) alone.
_TEXT_SUFFIXES = {".ts", ".vue", ".js", ".py", ".json", ".po", ".pot", ".html", ".md", ".css"}


def transform_text(text: str) -> str:
    for pattern, repl in _RULES:
        text = pattern.sub(repl, text)
    return text


def transform_rel(rel: Path) -> Path:
    """Apply the token rules to every component of a relative path."""
    return Path(*[transform_text(part) for part in rel.parts])


def _collision_counts(text: str) -> int:
    return len(_COLLISION_RE.findall(text))


class DriftError(Exception):
    pass


def process_file(path: Path, check: bool) -> bool:
    """Returns True if the file content changed (or would, in check mode)."""
    try:
        original = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return False
    transformed = transform_text(original)
    if transformed == original:
        return False
    before, after = _collision_counts(original), _collision_counts(transformed)
    if before != after:
        raise DriftError(f"{path}: collision-word count changed {before} -> {after}")
    if not check:
        path.write_text(transformed, encoding="utf-8")
    return True


def collect_files(root: Path, *, text_only: bool) -> list[Path]:
    return [
        p
        for p in root.rglob("*")
        if p.is_file()
        and "__pycache__" not in p.parts
        and (not text_only or p.suffix in _TEXT_SUFFIXES)
    ]


def plan_renames(root: Path, files: list[Path]) -> list[tuple[Path, Path]]:
    """Map each file to its fully transformed relative path and abort on any
    collision. A collision means the term-rename would land two files on the
    same path (e.g. FolderTreeBoard.vue -> FolderTreeMap.vue, where a distinct
    treemap component FolderTreeMap.vue already exists) — silently clobbering
    one. These are genuine semantic clashes that need a human decision, so we
    fail loud instead of guessing."""
    targets: dict[Path, list[Path]] = {}
    renames: list[tuple[Path, Path]] = []
    for p in files:
        rel = p.relative_to(root)
        new_rel = transform_rel(rel)
        targets.setdefault(new_rel, []).append(rel)
        if new_rel != rel:
            renames.append((p, root / new_rel))

    collisions: list[str] = []
    existing = {p.relative_to(root) for p in files}
    for new_rel, sources in targets.items():
        if len(sources) > 1:
            collisions.append(f"{new_rel}  <-  {', '.join(str(s) for s in sources)}")
        elif new_rel != sources[0] and new_rel in existing:
            collisions.append(f"{new_rel}  (target already present, untouched)")
    if collisions:
        raise DriftError(
            "path rename collisions (resolve names by hand first):\n  " + "\n  ".join(collisions)
        )
    return renames


def apply_renames(root: Path, renames: list[tuple[Path, Path]]) -> None:
    for src, dst in renames:
        dst.parent.mkdir(parents=True, exist_ok=True)
        src.rename(dst)
    # prune directories that became empty after the moves
    for d in sorted(root.rglob("*"), key=lambda p: len(p.parts), reverse=True):
        if d.is_dir() and not any(d.iterdir()):
            d.rmdir()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("dirs", nargs="+", type=Path)
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    changed_files = 0
    path_renames: list[tuple[Path, Path]] = []
    try:
        for d in args.dirs:
            if not d.is_dir():
                print(f"ERROR: not a directory: {d}", file=sys.stderr)
                return 2
            # Plan (and collision-check) renames up front so a bad tree aborts
            # before any content is written.
            renames = plan_renames(d, collect_files(d, text_only=False))
            path_renames.extend(renames)
            for f in collect_files(d, text_only=True):
                if process_file(f, args.check):
                    changed_files += 1
            if not args.check:
                apply_renames(d, renames)
    except DriftError as e:
        print(f"ERROR: guard tripped — {e}", file=sys.stderr)
        return 1

    verb = "would change" if args.check else "changed"
    print(f"[rename-board-to-map] {verb} {changed_files} file(s), {len(path_renames)} path(s)")
    for src, dst in path_renames:
        print(f"  rename {src} -> {dst}")
    if args.check and (changed_files or path_renames):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
