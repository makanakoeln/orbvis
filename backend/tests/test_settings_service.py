"""Tests for global settings service and API endpoint."""

from __future__ import annotations

import json

import pytest

from app.schemas.settings import GlobalSettings
from app.services.settings_service import get_settings, save_settings


def _patch(monkeypatch, tmp_path):
    boards_dir = tmp_path / "boards"
    boards_dir.mkdir(exist_ok=True)
    monkeypatch.setattr("app.core.config.settings.boards_dir", str(boards_dir))
    monkeypatch.setattr("app.services.settings_service.settings.boards_dir", str(boards_dir))
    return boards_dir


# ---------------------------------------------------------------------------
# get_settings
# ---------------------------------------------------------------------------


def test_get_settings_returns_defaults_when_no_file(tmp_path, monkeypatch):
    _patch(monkeypatch, tmp_path)
    result = get_settings()
    assert isinstance(result, GlobalSettings)
    assert result.icon_size == 30


def test_get_settings_reads_existing_file(tmp_path, monkeypatch):
    _patch(monkeypatch, tmp_path)
    settings_file = tmp_path / "settings.json"
    settings_file.write_text(json.dumps({"icon_size": 64}), encoding="utf-8")
    result = get_settings()
    assert result.icon_size == 64


def test_get_settings_returns_defaults_on_malformed_json(tmp_path, monkeypatch):
    _patch(monkeypatch, tmp_path)
    settings_file = tmp_path / "settings.json"
    settings_file.write_text("not valid json!!", encoding="utf-8")
    result = get_settings()
    assert result.icon_size == 30  # fallback to default


# ---------------------------------------------------------------------------
# save_settings
# ---------------------------------------------------------------------------


def test_save_settings_writes_file(tmp_path, monkeypatch):
    _patch(monkeypatch, tmp_path)
    data = GlobalSettings(icon_size=64, default_backend_id="mybackend")
    result = save_settings(data)
    assert result == data
    settings_file = tmp_path / "settings.json"
    assert settings_file.is_file()
    loaded = json.loads(settings_file.read_text())
    assert loaded["icon_size"] == 64
    assert loaded["default_backend_id"] == "mybackend"


def test_save_settings_returns_same_data(tmp_path, monkeypatch):
    _patch(monkeypatch, tmp_path)
    data = GlobalSettings(icon_size=22)
    assert save_settings(data).icon_size == 22


# ---------------------------------------------------------------------------
# API endpoints
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_settings_api_authenticated(client, admin_token, tmp_path, monkeypatch):
    _patch(monkeypatch, tmp_path)
    response = await client.get(
        "/api/v1/settings", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    assert "icon_size" in response.json()


@pytest.mark.asyncio
async def test_get_settings_api_regular_user(client, regular_token, tmp_path, monkeypatch):
    _patch(monkeypatch, tmp_path)
    response = await client.get(
        "/api/v1/settings", headers={"Authorization": f"Bearer {regular_token}"}
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_put_settings_api_admin(client, admin_token, tmp_path, monkeypatch):
    _patch(monkeypatch, tmp_path)
    monkeypatch.setattr(
        "app.api.v1.settings.settings_service.settings.boards_dir", str(tmp_path / "boards")
    )
    response = await client.put(
        "/api/v1/settings",
        json={
            "icon_size": 48,
            "view_type": "icon",
            "label_show": True,
            "label_size": 11,
            "label_color": "#ffffff",
            "label_background": "transparent",
            "label_x": 0,
            "label_y": 0,
            "url_target": "_blank",
            "z": 1,
            "line_style": None,
            "default_backend_id": "live_1",
            "default_map_type": "static",
            "hover_template": None,
            "context_template": None,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["icon_size"] == 48


@pytest.mark.asyncio
async def test_put_settings_api_non_admin_forbidden(client, regular_token, tmp_path, monkeypatch):
    _patch(monkeypatch, tmp_path)
    response = await client.put(
        "/api/v1/settings",
        json={"icon_size": 48},
        headers={"Authorization": f"Bearer {regular_token}"},
    )
    assert response.status_code == 403
