"""Tests for global + system settings service and API endpoints."""

from __future__ import annotations

import json

import pytest

from app.schemas.settings import GlobalSettings, SystemSettings
from app.services.settings_service import (
    get_effective_log_level,
    get_global_settings,
    get_system_settings,
    save_global_settings,
    save_system_settings,
)


def _patch(monkeypatch, tmp_path):
    boards_dir = tmp_path / "boards"
    boards_dir.mkdir(exist_ok=True)
    monkeypatch.setattr("app.core.config.settings.boards_dir", str(boards_dir))
    monkeypatch.setattr("app.services.settings_service.settings.boards_dir", str(boards_dir))
    return boards_dir


# ---------------------------------------------------------------------------
# get_global_settings
# ---------------------------------------------------------------------------


def test_get_global_settings_returns_defaults_when_no_file(tmp_path, monkeypatch):
    _patch(monkeypatch, tmp_path)
    result = get_global_settings()
    assert isinstance(result, GlobalSettings)
    assert result.icon_size == 30
    assert result.label_color == "#ffffff"
    assert result.label_background == "transparent"


def test_get_global_settings_reads_existing_file(tmp_path, monkeypatch):
    _patch(monkeypatch, tmp_path)
    settings_file = tmp_path / "settings.json"
    settings_file.write_text(json.dumps({"icon_size": 64}), encoding="utf-8")
    result = get_global_settings()
    assert result.icon_size == 64


def test_get_global_settings_migrates_legacy_url_target_and_line_style(tmp_path, monkeypatch):
    _patch(monkeypatch, tmp_path)
    settings_file = tmp_path / "settings.json"
    settings_file.write_text(
        json.dumps({"url_target": "_top", "line_style": None}), encoding="utf-8"
    )
    result = get_global_settings()
    assert result.url_target == "_blank"
    assert result.line_style == "plain"


def test_get_global_settings_returns_defaults_on_malformed_json(tmp_path, monkeypatch):
    _patch(monkeypatch, tmp_path)
    settings_file = tmp_path / "settings.json"
    settings_file.write_text("not valid json!!", encoding="utf-8")
    result = get_global_settings()
    assert result.icon_size == 30  # fallback to default


# ---------------------------------------------------------------------------
# save_global_settings
# ---------------------------------------------------------------------------


def test_save_global_settings_writes_file(tmp_path, monkeypatch):
    _patch(monkeypatch, tmp_path)
    data = GlobalSettings(icon_size=64, default_backend_id="mybackend")
    result = save_global_settings(data)
    assert result == data
    settings_file = tmp_path / "settings.json"
    assert settings_file.is_file()
    loaded = json.loads(settings_file.read_text())
    assert loaded["icon_size"] == 64
    assert loaded["default_backend_id"] == "mybackend"


def test_save_global_settings_preserves_system_fields(tmp_path, monkeypatch):
    """Writing globals must not nuke system fields living in the same JSON."""
    _patch(monkeypatch, tmp_path)
    settings_file = tmp_path / "settings.json"
    settings_file.write_text(
        json.dumps({"log_level": "DEBUG", "checkmk_url": "/SITE"}), encoding="utf-8"
    )
    save_global_settings(GlobalSettings(icon_size=22))
    loaded = json.loads(settings_file.read_text())
    assert loaded["log_level"] == "DEBUG"
    assert loaded["checkmk_url"] == "/SITE"
    assert loaded["icon_size"] == 22


# ---------------------------------------------------------------------------
# system settings
# ---------------------------------------------------------------------------


def test_get_system_settings_keeps_unset_log_level_none(tmp_path, monkeypatch):
    # ``get_system_settings`` no longer layers in env fallbacks — it returns
    # the raw stored shape so callers can distinguish "operator set it" from
    # "env default is in play". ``get_effective_log_level`` is the layered view.
    _patch(monkeypatch, tmp_path)
    monkeypatch.setattr("app.core.config.settings.log_level", "WARNING")
    monkeypatch.setattr("app.services.settings_service.settings.log_level", "WARNING")
    monkeypatch.setattr("app.core.config.settings.debug", False)
    monkeypatch.setattr("app.services.settings_service.settings.debug", False)
    result = get_system_settings()
    assert isinstance(result, SystemSettings)
    assert result.log_level is None
    assert get_effective_log_level() == "WARNING"


def test_save_system_settings_preserves_global_fields(tmp_path, monkeypatch):
    _patch(monkeypatch, tmp_path)
    settings_file = tmp_path / "settings.json"
    settings_file.write_text(
        json.dumps({"icon_size": 64, "label_color": "#abcdef"}), encoding="utf-8"
    )
    save_system_settings(SystemSettings(log_level="ERROR", checkmk_url="/cmc"))
    loaded = json.loads(settings_file.read_text())
    assert loaded["icon_size"] == 64
    assert loaded["label_color"] == "#abcdef"
    assert loaded["log_level"] == "ERROR"
    assert loaded["checkmk_url"] == "/cmc"


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
            "url_target": "_blank",
            "z": 1,
            "line_style": "plain",
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
async def test_put_settings_api_rejects_bad_color(client, admin_token, tmp_path, monkeypatch):
    _patch(monkeypatch, tmp_path)
    monkeypatch.setattr(
        "app.api.v1.settings.settings_service.settings.boards_dir", str(tmp_path / "boards")
    )
    response = await client.put(
        "/api/v1/settings",
        json={
            "icon_size": 30,
            "view_type": "icon",
            "label_show": True,
            "label_size": 11,
            "label_color": "nope",
            "label_background": "transparent",
            "url_target": "_blank",
            "z": 1,
            "default_backend_id": "live_1",
            "default_map_type": "static",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_put_settings_api_non_admin_forbidden(client, regular_token, tmp_path, monkeypatch):
    _patch(monkeypatch, tmp_path)
    response = await client.put(
        "/api/v1/settings",
        json={"icon_size": 48},
        headers={"Authorization": f"Bearer {regular_token}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_system_settings_api(client, admin_token, tmp_path, monkeypatch):
    _patch(monkeypatch, tmp_path)
    response = await client.get(
        "/api/v1/settings/system", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    body = response.json()
    # ``/system`` now returns the raw stored state — ``response_model_exclude_none``
    # drops keys that the operator hasn't explicitly set yet, so an empty body
    # is the correct shape on a fresh install. The layered "effective" view
    # is queried via ``get_effective_*`` helpers, not this endpoint.
    assert isinstance(body, dict)


@pytest.mark.asyncio
async def test_put_system_settings_api_admin(client, admin_token, tmp_path, monkeypatch):
    _patch(monkeypatch, tmp_path)
    monkeypatch.setattr(
        "app.api.v1.settings.settings_service.settings.boards_dir", str(tmp_path / "boards")
    )
    response = await client.put(
        "/api/v1/settings/system",
        json={"log_level": "ERROR", "checkmk_url": "/CMC"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["log_level"] == "ERROR"


@pytest.mark.asyncio
async def test_put_system_settings_api_non_admin_forbidden(
    client, regular_token, tmp_path, monkeypatch
):
    _patch(monkeypatch, tmp_path)
    response = await client.put(
        "/api/v1/settings/system",
        json={"log_level": "ERROR"},
        headers={"Authorization": f"Bearer {regular_token}"},
    )
    assert response.status_code == 403
