"""Unit tests for the stdlib sqlite3 wrapper (``app.core.database``).

Cover the legacy-URL path resolution, the connection PRAGMAs, the ``get_db``
generator lifecycle and idempotent schema application — all against tmp / memory
databases so the shared test DB is left untouched.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from app.core import database


class TestResolveDbPath:
    @pytest.mark.parametrize(
        "url",
        [
            "sqlite+aiosqlite:////data/orbvis.db",
            "sqlite+pysqlite:////data/orbvis.db",
            "sqlite:////data/orbvis.db",
        ],
    )
    def test_strips_legacy_sqlalchemy_prefixes(
        self, url: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("app.core.config.settings.database_url", url)
        assert database._resolve_db_path() == "/data/orbvis.db"

    def test_relative_path_keeps_no_leading_slash(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("app.core.config.settings.database_url", "sqlite:///orbvis.db")
        assert database._resolve_db_path() == "orbvis.db"

    def test_empty_url_falls_back_to_memory(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("app.core.config.settings.database_url", "")
        assert database._resolve_db_path() == ":memory:"


class TestConnect:
    def test_connection_uses_row_factory_and_pragmas(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        db = tmp_path / "t.db"
        monkeypatch.setattr("app.core.config.settings.database_url", f"sqlite:///{db}")
        conn = database._connect()
        try:
            assert conn.row_factory is sqlite3.Row
            fk = conn.execute("PRAGMA foreign_keys").fetchone()[0]
            assert fk == 1
            # WAL is the persisted journal mode for an on-disk database.
            mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
            assert mode.lower() == "wal"
        finally:
            conn.close()


class TestGetDb:
    async def test_yields_one_connection_and_closes_it(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        db = tmp_path / "t.db"
        monkeypatch.setattr("app.core.config.settings.database_url", f"sqlite:///{db}")
        gen = database.get_db()
        conn = await anext(gen)
        assert conn.execute("SELECT 1").fetchone()[0] == 1
        with pytest.raises(StopAsyncIteration):
            await anext(gen)
        # Connection is closed after the generator is exhausted.
        with pytest.raises(sqlite3.ProgrammingError):
            conn.execute("SELECT 1")


class TestEnsureSchema:
    def test_creates_tables_and_is_idempotent(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        db = tmp_path / "fresh.db"
        monkeypatch.setattr("app.core.config.settings.database_url", f"sqlite:///{db}")
        database._ensure_schema()
        # A second pass must not raise (CREATE TABLE IF NOT EXISTS etc.).
        database._ensure_schema()
        conn = database._connect()
        try:
            tables = {
                r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            }
            assert "users" in tables
        finally:
            conn.close()

    def test_drops_legacy_alembic_version_table(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        db = tmp_path / "legacy.db"
        monkeypatch.setattr("app.core.config.settings.database_url", f"sqlite:///{db}")
        seed = database._connect()
        try:
            seed.execute("CREATE TABLE alembic_version (version_num TEXT)")
        finally:
            seed.close()
        database._ensure_schema()
        conn = database._connect()
        try:
            row = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='alembic_version'"
            ).fetchone()
            assert row is None
        finally:
            conn.close()
