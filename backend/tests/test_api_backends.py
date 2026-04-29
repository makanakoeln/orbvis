"""Tests for the backends API endpoints."""

from __future__ import annotations

import pytest

from app.api.v1.backends import _parse_metric_names
from app.services import state_service


def _patch(monkeypatch, tmp_path):
    backends_file = tmp_path / "backends.json"
    monkeypatch.setattr("app.core.config.settings.backends_file", str(backends_file))
    monkeypatch.setattr("app.services.backend_service.settings.backends_file", str(backends_file))
    return backends_file


_SAMPLE_BACKEND = {
    "id": "live_1",
    "type": "livestatus",
    "label": "Test Backend",
    "socket_path": "/tmp/live",  # nosec B108
}


# ---------------------------------------------------------------------------
# _parse_metric_names — pure unit tests
# ---------------------------------------------------------------------------


def test_parse_metric_names_simple():
    assert _parse_metric_names("rta=1.5ms;50;200;0;") == ["rta"]


def test_parse_metric_names_multiple():
    result = _parse_metric_names("load1=0.5;1;2 load5=0.3;1;2")
    assert result == ["load1", "load5"]


def test_parse_metric_names_quoted_label():
    result = _parse_metric_names("'load average'=0.5;1;2")
    assert result == ["load average"]


def test_parse_metric_names_empty():
    assert _parse_metric_names("") == []


# ---------------------------------------------------------------------------
# Backends CRUD
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_backends_empty(client, admin_token, tmp_path, monkeypatch):
    _patch(monkeypatch, tmp_path)
    response = await client.get(
        "/api/v1/backends", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_list_backends_non_admin_forbidden(
    client, regular_token, regular_user, tmp_path, monkeypatch
):
    _patch(monkeypatch, tmp_path)
    response = await client.get(
        "/api/v1/backends", headers={"Authorization": f"Bearer {regular_token}"}
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_create_backend(client, admin_token, tmp_path, monkeypatch):
    _patch(monkeypatch, tmp_path)
    response = await client.post(
        "/api/v1/backends",
        json=_SAMPLE_BACKEND,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 201
    assert response.json()["id"] == "live_1"


@pytest.mark.asyncio
async def test_create_backend_duplicate_id(client, admin_token, tmp_path, monkeypatch):
    _patch(monkeypatch, tmp_path)
    await client.post(
        "/api/v1/backends",
        json=_SAMPLE_BACKEND,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    response = await client.post(
        "/api/v1/backends",
        json=_SAMPLE_BACKEND,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_update_backend(client, admin_token, tmp_path, monkeypatch):
    _patch(monkeypatch, tmp_path)
    await client.post(
        "/api/v1/backends",
        json=_SAMPLE_BACKEND,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    response = await client.put(
        "/api/v1/backends/live_1",
        json={"type": "livestatus", "label": "Updated", "socket_path": "/tmp/live2"},  # nosec B108
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["label"] == "Updated"


@pytest.mark.asyncio
async def test_update_backend_not_found(client, admin_token, tmp_path, monkeypatch):
    _patch(monkeypatch, tmp_path)
    response = await client.put(
        "/api/v1/backends/nonexistent",
        json={"type": "livestatus", "label": "X"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_backends_redacts_secrets(client, admin_token, tmp_path, monkeypatch):
    """GET /backends must never return raw automation_secret values."""
    _patch(monkeypatch, tmp_path)
    await client.post(
        "/api/v1/backends",
        json={**_SAMPLE_BACKEND, "automation_secret": "very-secret-token"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    response = await client.get(
        "/api/v1/backends", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body[0]["automation_secret"] == "***REDACTED***"
    assert "very-secret-token" not in response.text


@pytest.mark.asyncio
async def test_update_backend_preserves_secret_when_redacted_sent(
    client, admin_token, tmp_path, monkeypatch
):
    """Frontend echoes the redaction sentinel when the admin doesn't retype the
    secret — backend must keep the previously stored value, not overwrite with
    the sentinel string."""
    _patch(monkeypatch, tmp_path)
    await client.post(
        "/api/v1/backends",
        json={**_SAMPLE_BACKEND, "automation_secret": "real-secret"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    response = await client.put(
        "/api/v1/backends/live_1",
        json={
            "type": "livestatus",
            "label": "Updated",
            "socket_path": "/tmp/live",  # nosec B108
            "automation_secret": "***REDACTED***",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    # The redacted sentinel was preserved server-side; reload via service to
    # confirm the on-disk value is still the original.
    from app.services import backend_service

    cfg = next(b for b in backend_service.load_all() if b.id == "live_1")
    assert cfg.automation_secret == "real-secret"


@pytest.mark.asyncio
async def test_create_backend_rejects_redacted_sentinel(client, admin_token, tmp_path, monkeypatch):
    _patch(monkeypatch, tmp_path)
    response = await client.post(
        "/api/v1/backends",
        json={**_SAMPLE_BACKEND, "automation_secret": "***REDACTED***"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_delete_backend(client, admin_token, tmp_path, monkeypatch):
    _patch(monkeypatch, tmp_path)
    await client.post(
        "/api/v1/backends",
        json=_SAMPLE_BACKEND,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    response = await client.delete(
        "/api/v1/backends/live_1", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_delete_backend_not_found(client, admin_token, tmp_path, monkeypatch):
    _patch(monkeypatch, tmp_path)
    response = await client.delete(
        "/api/v1/backends/nonexistent", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# GET /backends/{id}/test
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_test_backend_available(client, admin_token, mock_backend, monkeypatch):
    mock_backend.is_available.return_value = True
    monkeypatch.setitem(state_service._backends, "live_test", mock_backend)

    response = await client.get(
        "/api/v1/backends/live_test/test",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["ok"] is True


@pytest.mark.asyncio
async def test_test_backend_unavailable(client, admin_token, mock_backend, monkeypatch):
    mock_backend.is_available.return_value = False
    monkeypatch.setitem(state_service._backends, "live_test2", mock_backend)

    response = await client.get(
        "/api/v1/backends/live_test2/test",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["ok"] is False


@pytest.mark.asyncio
async def test_test_backend_exception(client, admin_token, mock_backend, monkeypatch):
    from unittest.mock import AsyncMock

    mock_backend.is_available = AsyncMock(side_effect=Exception("Connection refused"))
    monkeypatch.setitem(state_service._backends, "live_test3", mock_backend)

    response = await client.get(
        "/api/v1/backends/live_test3/test",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["ok"] is False
    assert "Connection refused" in response.json()["message"]


@pytest.mark.asyncio
async def test_test_backend_not_registered(client, admin_token, tmp_path, monkeypatch):
    # Ensure a clean _backends dict without this ID
    monkeypatch.setattr(state_service, "_backends", {})

    response = await client.get(
        "/api/v1/backends/unregistered/test",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# POST /backends/test-connection
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_test_connection_success(client, admin_token, mock_backend, monkeypatch):
    from unittest.mock import patch

    with patch("app.services.backend_service.build_instance", return_value=mock_backend):
        response = await client.post(
            "/api/v1/backends/test-connection",
            json=_SAMPLE_BACKEND,
            headers={"Authorization": f"Bearer {admin_token}"},
        )
    assert response.status_code == 200
    assert response.json()["ok"] is True


@pytest.mark.asyncio
async def test_test_connection_failure(client, admin_token, mock_backend, monkeypatch):
    from unittest.mock import AsyncMock, patch

    mock_backend.is_available = AsyncMock(side_effect=Exception("refused"))

    with patch("app.services.backend_service.build_instance", return_value=mock_backend):
        response = await client.post(
            "/api/v1/backends/test-connection",
            json=_SAMPLE_BACKEND,
            headers={"Authorization": f"Bearer {admin_token}"},
        )
    assert response.status_code == 200
    assert response.json()["ok"] is False
