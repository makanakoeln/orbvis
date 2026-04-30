"""Tests for the demo-board seeder."""

from __future__ import annotations

from pathlib import Path

from app.seed_boards import MARKER_NAME, SEED_DIR, seed_demo_boards


def test_seed_into_empty_dir_copies_demos(tmp_path: Path) -> None:
    boards_dir = tmp_path / "boards"

    seed_demo_boards(boards_dir)

    seeded_jsons = sorted(p.name for p in boards_dir.glob("*.json"))
    bundled_jsons = sorted(p.name for p in SEED_DIR.glob("*.json"))
    assert seeded_jsons == bundled_jsons
    assert (boards_dir / MARKER_NAME).is_file()
    assert (boards_dir / "backgrounds" / "demo.svg").is_file()


def test_seed_is_idempotent_via_marker(tmp_path: Path) -> None:
    boards_dir = tmp_path / "boards"
    seed_demo_boards(boards_dir)

    for json_file in boards_dir.glob("*.json"):
        json_file.unlink()

    seed_demo_boards(boards_dir)

    assert (boards_dir / MARKER_NAME).is_file()
    assert list(boards_dir.glob("*.json")) == []


def test_existing_install_gets_marker_without_copy(tmp_path: Path) -> None:
    boards_dir = tmp_path / "boards"
    boards_dir.mkdir()
    (boards_dir / "user-board.json").write_text('{"name":"user-board"}')

    seed_demo_boards(boards_dir)

    assert (boards_dir / MARKER_NAME).is_file()
    assert sorted(p.name for p in boards_dir.glob("*.json")) == ["user-board.json"]


def test_creates_dir_if_missing(tmp_path: Path) -> None:
    boards_dir = tmp_path / "does-not-exist-yet"

    seed_demo_boards(boards_dir)

    assert boards_dir.is_dir()
    assert (boards_dir / MARKER_NAME).is_file()
