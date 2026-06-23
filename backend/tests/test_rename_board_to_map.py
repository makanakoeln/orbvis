"""Guards for the board->map migration codemod (scripts/rename-board-to-map.py).

The codemod produces the built-in Checkmk ("Maps") variant; a regression in its
identifier-boundary rules would silently corrupt the generated package, so the
boundary behaviour and the collision guards are pinned here.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "rename-board-to-map.py"
_spec = importlib.util.spec_from_file_location("rename_board_to_map", _SCRIPT)
assert _spec and _spec.loader
codemod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(codemod)


@pytest.mark.parametrize(
    ("src", "expected"),
    [
        # OrbVis domain term -> renamed
        ("board", "map"),
        ("Board", "Map"),
        ("boards", "maps"),
        ("Boards", "Maps"),
        ("BOARD_DIR", "MAP_DIR"),
        ("BOARDS_DIR", "MAPS_DIR"),
        ("currentBoard", "currentMap"),
        ("BoardObject", "MapObject"),
        ("useBoardsStore", "useMapsStore"),
        ("board_service", "map_service"),
        ("/api/v1/boards", "/api/v1/maps"),
        ("'@/components/board/BoardCanvas.vue'", "'@/components/map/MapCanvas.vue'"),
        ("seed_boards", "seed_maps"),
    ],
)
def test_renames_orbvis_term(src: str, expected: str) -> None:
    assert codemod.transform_text(src) == expected


@pytest.mark.parametrize(
    "word",
    [
        "dashboard",
        "Dashboard",
        "dashboards",
        "keyboard",
        "KeyboardEvent",
        "clipboard",
        "Clipboard",
        "copyToClipboard",
        "checkerboard",
        "boarding",  # board + lowercase continuation is a different word
        "boarded",
    ],
)
def test_leaves_collision_words_untouched(word: str) -> None:
    assert codemod.transform_text(word) == word


def test_collision_word_in_context_survives() -> None:
    line = "function onKeyDown(e: KeyboardEvent) { board.reset() }"
    assert codemod.transform_text(line) == ("function onKeyDown(e: KeyboardEvent) { map.reset() }")


def test_plan_renames_aborts_on_semantic_collision(tmp_path: Path) -> None:
    # FolderTreeBoard.vue -> FolderTreeMap.vue collides with a pre-existing
    # treemap component of the same target name.
    (tmp_path / "FolderTreeBoard.vue").write_text("x", encoding="utf-8")
    (tmp_path / "FolderTreeMap.vue").write_text("y", encoding="utf-8")
    files = codemod.collect_files(tmp_path, text_only=False)
    with pytest.raises(codemod.DriftError):
        codemod.plan_renames(tmp_path, files)


def test_plan_renames_ok_without_collision(tmp_path: Path) -> None:
    (tmp_path / "BoardCanvas.vue").write_text("x", encoding="utf-8")
    renames = codemod.plan_renames(tmp_path, codemod.collect_files(tmp_path, text_only=False))
    assert [(s.name, d.name) for s, d in renames] == [("BoardCanvas.vue", "MapCanvas.vue")]
