"""board_service CRUD + helper logic.

Complements ``test_board_service_io.py`` (which focuses on the debounced-flush /
atomic-write machinery) by covering the create/update/clone/import/reorder paths,
the path-traversal guard, sticky-connector cleanup and the legacy-key migration —
all against a tmp boards dir so nothing touches the real data directory.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.schemas.board import (
    BoardCreate,
    BoardObject,
    BoardObjectUpdate,
    BoardUpdate,
)
from app.services import board_service
from app.services.board_service import StaleBoardError


@pytest.fixture
def boards_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    d = tmp_path / "boards"
    d.mkdir()
    monkeypatch.setattr("app.core.config.settings.boards_dir", str(d))
    monkeypatch.setattr("app.services.board_service.settings.boards_dir", str(d))
    return d


def _obj(obj_id: str, **kw: object) -> BoardObject:
    return BoardObject(id=obj_id, type=kw.pop("type", "textbox"), x=0, y=0, **kw)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# create_board
# ---------------------------------------------------------------------------


class TestCreateBoard:
    def test_creates_and_reads_back(self, boards_dir: Path) -> None:
        cfg = board_service.create_board(BoardCreate(name="b1", alias="One"))
        assert cfg.name == "b1"
        assert board_service.get_board("b1") is not None

    def test_rejects_duplicate_name(self, boards_dir: Path) -> None:
        board_service.create_board(BoardCreate(name="dup"))
        with pytest.raises(ValueError, match="already exists"):
            board_service.create_board(BoardCreate(name="dup"))

    def test_rejects_case_insensitive_duplicate(self, boards_dir: Path) -> None:
        board_service.create_board(BoardCreate(name="Folder"))
        with pytest.raises(ValueError, match="already exists"):
            board_service.create_board(BoardCreate(name="folder"))


# ---------------------------------------------------------------------------
# update_board
# ---------------------------------------------------------------------------


class TestUpdateBoard:
    def test_merges_and_bumps_version(self, boards_dir: Path) -> None:
        created = board_service.create_board(BoardCreate(name="upd"))
        updated = board_service.update_board("upd", BoardUpdate(alias="New alias"))
        assert updated is not None
        assert updated.alias == "New alias"
        assert updated.version == created.version + 1

    def test_missing_board_returns_none(self, boards_dir: Path) -> None:
        assert board_service.update_board("ghost", BoardUpdate(alias="x")) is None

    def test_empty_update_is_a_noop(self, boards_dir: Path) -> None:
        created = board_service.create_board(BoardCreate(name="noop"))
        updated = board_service.update_board("noop", BoardUpdate())
        assert updated is not None
        assert updated.version == created.version

    def test_stale_version_raises(self, boards_dir: Path) -> None:
        board_service.create_board(BoardCreate(name="stale"))
        with pytest.raises(StaleBoardError) as exc:
            board_service.update_board("stale", BoardUpdate(alias="x"), expected_version=999)
        assert exc.value.current_version == 0


# ---------------------------------------------------------------------------
# add / update / delete object
# ---------------------------------------------------------------------------


class TestObjectMutations:
    def test_add_object(self, boards_dir: Path) -> None:
        board_service.create_board(BoardCreate(name="ob"))
        cfg = board_service.add_object("ob", _obj("o1"))
        assert cfg is not None
        assert [o.id for o in cfg.objects] == ["o1"]

    def test_add_duplicate_id_raises(self, boards_dir: Path) -> None:
        board_service.create_board(BoardCreate(name="ob"))
        board_service.add_object("ob", _obj("o1"))
        with pytest.raises(ValueError, match="already exists"):
            board_service.add_object("ob", _obj("o1"))

    def test_add_object_missing_board_returns_none(self, boards_dir: Path) -> None:
        assert board_service.add_object("ghost", _obj("o1")) is None

    def test_update_object_merges_fields(self, boards_dir: Path) -> None:
        board_service.create_board(BoardCreate(name="ob"))
        board_service.add_object("ob", _obj("o1"))
        new = board_service.update_object("ob", "o1", BoardObjectUpdate(x=42, y=7))
        assert new is not None
        assert new.x == 42
        assert new.y == 7

    def test_update_unknown_object_returns_none(self, boards_dir: Path) -> None:
        board_service.create_board(BoardCreate(name="ob"))
        assert board_service.update_object("ob", "absent", BoardObjectUpdate(x=1)) is None

    def test_delete_object(self, boards_dir: Path) -> None:
        board_service.create_board(BoardCreate(name="ob"))
        board_service.add_object("ob", _obj("o1"))
        assert board_service.delete_object("ob", "o1") is True
        cfg = board_service.get_board("ob")
        assert cfg is not None
        assert cfg.objects == []

    def test_delete_unknown_object_returns_false(self, boards_dir: Path) -> None:
        board_service.create_board(BoardCreate(name="ob"))
        assert board_service.delete_object("ob", "absent") is False

    def test_delete_object_clears_dangling_connector_refs(self, boards_dir: Path) -> None:
        board_service.create_board(BoardCreate(name="ob"))
        board_service.add_object("ob", _obj("anchor"))
        board_service.add_object(
            "ob", _obj("conn", type="line", start_ref="anchor", end_ref="anchor")
        )
        board_service.delete_object("ob", "anchor")
        cfg = board_service.get_board("ob")
        assert cfg is not None
        line = next(o for o in cfg.objects if o.id == "conn")
        assert line.start_ref is None
        assert line.end_ref is None


# ---------------------------------------------------------------------------
# clone / import / reorder
# ---------------------------------------------------------------------------


class TestCloneBoard:
    def test_clone_copies_objects_and_resets_readonly(self, boards_dir: Path) -> None:
        board_service.create_board(BoardCreate(name="src"))
        board_service.add_object("src", _obj("o1"))
        clone = board_service.clone_board("src", "dst", alias="Copy")
        assert clone.name == "dst"
        assert clone.alias == "Copy"
        assert clone.readonly is False
        assert [o.id for o in clone.objects] == ["o1"]

    def test_clone_missing_source_raises(self, boards_dir: Path) -> None:
        with pytest.raises(ValueError, match="not found"):
            board_service.clone_board("ghost", "dst")

    def test_clone_onto_existing_name_raises(self, boards_dir: Path) -> None:
        board_service.create_board(BoardCreate(name="src"))
        board_service.create_board(BoardCreate(name="taken"))
        with pytest.raises(ValueError, match="already exists"):
            board_service.clone_board("src", "taken")


class TestImportBoard:
    def _payload(self, name: str) -> dict[str, object]:
        return {"name": name, "alias": "Imported", "objects": []}

    def test_import_creates_board(self, boards_dir: Path) -> None:
        cfg = board_service.import_board(self._payload("imp"))
        assert cfg.name == "imp"
        assert board_service.get_board("imp") is not None

    def test_import_rejects_existing_without_overwrite(self, boards_dir: Path) -> None:
        board_service.import_board(self._payload("imp"))
        with pytest.raises(ValueError, match="already exists"):
            board_service.import_board(self._payload("imp"))

    def test_import_overwrites_when_requested(self, boards_dir: Path) -> None:
        board_service.import_board(self._payload("imp"))
        cfg = board_service.import_board(
            {"name": "imp", "alias": "Replaced", "objects": []}, overwrite=True
        )
        assert cfg.alias == "Replaced"

    def test_import_rejects_unsafe_name(self, boards_dir: Path) -> None:
        with pytest.raises(ValueError, match="invalid"):
            board_service.import_board(self._payload("../etc/passwd"))


class TestReorderBoards:
    def test_updates_sort_order_and_bumps_version(self, boards_dir: Path) -> None:
        board_service.create_board(BoardCreate(name="a"))
        board_service.create_board(BoardCreate(name="b"))
        board_service.reorder_boards([("a", 5), ("b", 2)])
        a = board_service.get_board("a")
        b = board_service.get_board("b")
        assert a is not None and a.sort_order == 5
        assert b is not None and b.sort_order == 2

    def test_unknown_names_are_skipped(self, boards_dir: Path) -> None:
        board_service.create_board(BoardCreate(name="a"))
        # Must not raise on the unknown name.
        board_service.reorder_boards([("a", 1), ("ghost", 9)])
        a = board_service.get_board("a")
        assert a is not None and a.sort_order == 1


# ---------------------------------------------------------------------------
# path safety + helpers
# ---------------------------------------------------------------------------


class TestPathSafety:
    @pytest.mark.parametrize("bad", ["../escape", "with/slash", "dot.dot", "space name"])
    def test_board_path_rejects_unsafe_names(self, boards_dir: Path, bad: str) -> None:
        with pytest.raises(ValueError, match="Invalid board name"):
            board_service._board_path(bad)

    def test_get_board_unsafe_name_returns_none(self, boards_dir: Path) -> None:
        assert board_service.get_board("../escape") is None

    def test_delete_board_unsafe_name_returns_false(self, boards_dir: Path) -> None:
        assert board_service.delete_board("../escape") is False


class TestLegacyMigration:
    def test_replace_key_recursive_renames_nested_keys(self) -> None:
        data: dict[str, object] = {"backend_id": "x", "objects": [{"backend_id": "y"}]}
        changed = board_service._replace_key_recursive(data, "backend_id", "connection_id")
        assert changed is True
        assert data["connection_id"] == "x"
        assert data["objects"][0]["connection_id"] == "y"  # type: ignore[index]

    def test_replace_key_recursive_noop_when_absent(self) -> None:
        data: dict[str, object] = {"connection_id": "x"}
        assert board_service._replace_key_recursive(data, "backend_id", "connection_id") is False

    def test_migrate_legacy_keys_rewrites_file(self, boards_dir: Path) -> None:
        legacy = boards_dir / "legacy.json"
        legacy.write_text(
            json.dumps({"name": "legacy", "backend_id": "conn1", "objects": []}),
            encoding="utf-8",
        )
        board_service.migrate_legacy_keys()
        data = json.loads(legacy.read_text())
        assert "backend_id" not in data
        assert data["connection_id"] == "conn1"
