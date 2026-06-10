"""board_service file I/O: debounced flush, atomic rename, delete invalidation."""

from __future__ import annotations

import json
import threading
from pathlib import Path

import pytest

from app.schemas.board import BoardCreate
from app.services import board_service


@pytest.fixture
def boards_dir(tmp_path, monkeypatch):
    d = tmp_path / "boards"
    d.mkdir()
    monkeypatch.setattr("app.core.config.settings.boards_dir", str(d))
    monkeypatch.setattr("app.services.board_service.settings.boards_dir", str(d))
    return d


def test_create_flushes_to_disk_via_flush_all(boards_dir: Path):
    board_service.create_board(BoardCreate(name="io-board", alias="IO"))
    # The write is debounced — flush_all (the shutdown path) must persist it.
    board_service.flush_all()
    data = json.loads((boards_dir / "io-board.json").read_text())
    assert data["name"] == "io-board"
    assert data["alias"] == "IO"


def test_debounce_coalesces_rapid_writes_to_one_timer(boards_dir: Path):
    board_service.create_board(BoardCreate(name="deb-board"))
    cfg = board_service.get_board("deb-board")
    assert cfg is not None
    for i in range(5):
        cfg.sort_order = i
        with board_service._board_lock("deb-board"):
            board_service._save_board(cfg.model_copy(deep=True))
    # One pending timer for the board, not five stacked ones.
    timers = [t for n, t in board_service._FLUSH_TIMERS.items() if n == "deb-board"]
    assert len(timers) == 1
    board_service.flush_all()
    data = json.loads((boards_dir / "deb-board.json").read_text())
    assert data["sort_order"] == 4


def test_flush_writes_atomically_no_temp_residue(boards_dir: Path):
    board_service.create_board(BoardCreate(name="atomic-board"))
    board_service.flush_all()
    leftovers = [p.name for p in boards_dir.iterdir() if p.suffix != ".json"]
    assert leftovers == []
    assert (boards_dir / "atomic-board.json").exists()


def test_failed_flush_remarks_dirty_for_retry(boards_dir: Path, monkeypatch):
    board_service.create_board(BoardCreate(name="retry-board"))

    def boom(cfg):
        raise OSError("disk full")

    monkeypatch.setattr(board_service, "_save_board_file", boom)
    board_service._flush("retry-board")
    assert "retry-board" in board_service._DIRTY

    monkeypatch.undo()
    monkeypatch.setattr("app.core.config.settings.boards_dir", str(boards_dir))
    monkeypatch.setattr("app.services.board_service.settings.boards_dir", str(boards_dir))
    board_service.flush_all()
    assert (boards_dir / "retry-board.json").exists()


def test_delete_cancels_pending_flush(boards_dir: Path):
    board_service.create_board(BoardCreate(name="del-board"))
    assert board_service.delete_board("del-board") is True
    # The stale debounced timer must not resurrect the file.
    board_service.flush_all()
    assert not (boards_dir / "del-board.json").exists()
    assert board_service.get_board("del-board") is None


def test_concurrent_writers_do_not_lose_objects(boards_dir: Path):
    board_service.create_board(BoardCreate(name="conc-board"))

    def add_objects(prefix: str) -> None:
        from app.schemas.board import BoardObject

        for i in range(10):
            board_service.add_object(
                "conc-board", BoardObject(id=f"{prefix}-{i}", type="textbox", x=0, y=0)
            )

    t1 = threading.Thread(target=add_objects, args=("a",))
    t2 = threading.Thread(target=add_objects, args=("b",))
    t1.start()
    t2.start()
    t1.join(timeout=30)
    t2.join(timeout=30)
    board_service.flush_all()
    data = json.loads((boards_dir / "conc-board.json").read_text())
    assert len(data["objects"]) == 20
