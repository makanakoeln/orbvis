"""Tests for the connections API endpoints."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.api.v1 import connections as connections_api
from app.api.v1.connections import _parse_metric_names
from app.schemas.state import ServicesSummary
from app.services import state_service


def _patch(monkeypatch, tmp_path):
    connections_file = tmp_path / "connections.json"
    monkeypatch.setattr("app.core.config.settings.connections_file", str(connections_file))
    monkeypatch.setattr(
        "app.services.connection_service.settings.connections_file", str(connections_file)
    )
    return connections_file


_SAMPLE_BACKEND = {
    "id": "live_1",
    "type": "livestatus",
    "label": "Test Connection",
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
# Connections CRUD
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_backends_empty(client, admin_token, tmp_path, monkeypatch):
    _patch(monkeypatch, tmp_path)
    response = await client.get(
        "/api/v1/connections", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_list_backends_non_admin_forbidden(
    client, regular_token, regular_user, tmp_path, monkeypatch
):
    _patch(monkeypatch, tmp_path)
    response = await client.get(
        "/api/v1/connections", headers={"Authorization": f"Bearer {regular_token}"}
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_create_backend(client, admin_token, tmp_path, monkeypatch):
    _patch(monkeypatch, tmp_path)
    response = await client.post(
        "/api/v1/connections",
        json=_SAMPLE_BACKEND,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 201
    assert response.json()["id"] == "live_1"


@pytest.mark.asyncio
async def test_create_backend_duplicate_id(client, admin_token, tmp_path, monkeypatch):
    _patch(monkeypatch, tmp_path)
    await client.post(
        "/api/v1/connections",
        json=_SAMPLE_BACKEND,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    response = await client.post(
        "/api/v1/connections",
        json=_SAMPLE_BACKEND,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_update_backend(client, admin_token, tmp_path, monkeypatch):
    _patch(monkeypatch, tmp_path)
    await client.post(
        "/api/v1/connections",
        json=_SAMPLE_BACKEND,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    response = await client.put(
        "/api/v1/connections/live_1",
        json={"type": "livestatus", "label": "Updated", "socket_path": "/tmp/live2"},  # nosec B108
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["label"] == "Updated"


@pytest.mark.asyncio
async def test_update_backend_not_found(client, admin_token, tmp_path, monkeypatch):
    _patch(monkeypatch, tmp_path)
    response = await client.put(
        "/api/v1/connections/nonexistent",
        json={"type": "livestatus", "label": "X"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_backends_redacts_secrets(client, admin_token, tmp_path, monkeypatch):
    """GET /connections must never return raw automation_secret values."""
    _patch(monkeypatch, tmp_path)
    await client.post(
        "/api/v1/connections",
        json={**_SAMPLE_BACKEND, "automation_secret": "very-secret-token"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    response = await client.get(
        "/api/v1/connections", headers={"Authorization": f"Bearer {admin_token}"}
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
    secret — connection must keep the previously stored value, not overwrite with
    the sentinel string."""
    _patch(monkeypatch, tmp_path)
    await client.post(
        "/api/v1/connections",
        json={**_SAMPLE_BACKEND, "automation_secret": "real-secret"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    response = await client.put(
        "/api/v1/connections/live_1",
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
    from app.services import connection_service

    cfg = next(b for b in connection_service.load_all() if b.id == "live_1")
    assert cfg.automation_secret == "real-secret"


@pytest.mark.asyncio
async def test_create_backend_rejects_redacted_sentinel(client, admin_token, tmp_path, monkeypatch):
    _patch(monkeypatch, tmp_path)
    response = await client.post(
        "/api/v1/connections",
        json={**_SAMPLE_BACKEND, "automation_secret": "***REDACTED***"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_delete_backend(client, admin_token, tmp_path, monkeypatch):
    _patch(monkeypatch, tmp_path)
    await client.post(
        "/api/v1/connections",
        json=_SAMPLE_BACKEND,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    response = await client.delete(
        "/api/v1/connections/live_1", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_delete_backend_not_found(client, admin_token, tmp_path, monkeypatch):
    _patch(monkeypatch, tmp_path)
    response = await client.delete(
        "/api/v1/connections/nonexistent", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# GET /connections/{id}/test
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_test_backend_available(client, admin_token, mock_connection, monkeypatch):
    mock_connection.is_available.return_value = True
    monkeypatch.setitem(state_service._connections, "live_test", mock_connection)

    response = await client.get(
        "/api/v1/connections/live_test/test",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["ok"] is True


@pytest.mark.asyncio
async def test_test_backend_unavailable(client, admin_token, mock_connection, monkeypatch):
    mock_connection.is_available.return_value = False
    monkeypatch.setitem(state_service._connections, "live_test2", mock_connection)

    response = await client.get(
        "/api/v1/connections/live_test2/test",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["ok"] is False


@pytest.mark.asyncio
async def test_test_backend_exception(client, admin_token, mock_connection, monkeypatch):
    from unittest.mock import AsyncMock

    mock_connection.is_available = AsyncMock(side_effect=Exception("Connection refused"))
    monkeypatch.setitem(state_service._connections, "live_test3", mock_connection)

    response = await client.get(
        "/api/v1/connections/live_test3/test",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["ok"] is False
    assert "Connection refused" in response.json()["message"]


@pytest.mark.asyncio
async def test_test_backend_not_registered(client, admin_token, tmp_path, monkeypatch):
    # Ensure a clean _backends dict without this ID
    monkeypatch.setattr(state_service, "_connections", {})

    response = await client.get(
        "/api/v1/connections/unregistered/test",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# POST /connections/test-connection
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_test_connection_success(client, admin_token, mock_connection, monkeypatch):
    from unittest.mock import patch

    with patch("app.services.connection_service.build_instance", return_value=mock_connection):
        response = await client.post(
            "/api/v1/connections/test-connection",
            json=_SAMPLE_BACKEND,
            headers={"Authorization": f"Bearer {admin_token}"},
        )
    assert response.status_code == 200
    assert response.json()["ok"] is True


@pytest.mark.asyncio
async def test_test_connection_failure(client, admin_token, mock_connection, monkeypatch):
    from unittest.mock import AsyncMock, patch

    mock_connection.is_available = AsyncMock(side_effect=Exception("refused"))

    with patch("app.services.connection_service.build_instance", return_value=mock_connection):
        response = await client.post(
            "/api/v1/connections/test-connection",
            json=_SAMPLE_BACKEND,
            headers={"Authorization": f"Bearer {admin_token}"},
        )
    assert response.status_code == 200
    assert response.json()["ok"] is False


# ---------------------------------------------------------------------------
# GET /connections/{id}/topology — bulk fetch, caching, truncation
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clear_topology_cache():
    connections_api._topology_cache.clear()
    yield
    connections_api._topology_cache.clear()


def _topology_row(name: str, parents: list[str] | None = None) -> dict:
    return {
        "name": name,
        "parents": parents or [],
        "state": "UP",
        "output": "ok",
    }


@pytest.mark.asyncio
async def test_topology_uses_bulk_services_query(client, admin_token, mock_connection, monkeypatch):
    """include_services must call get_hosts_services_batch once, not get_host_services per host."""
    monkeypatch.setitem(state_service._connections, "live_topo1", mock_connection)
    mock_connection.get_topology.return_value = [
        _topology_row("h1"),
        _topology_row("h2"),
        _topology_row("h3"),
    ]
    mock_connection.get_hosts_services_batch.return_value = {
        "h1": [{"name": "cpu", "state": "OK", "output": "fine"}],
        "h2": [],
        "h3": [{"name": "mem", "state": "WARNING", "output": "high"}],
    }

    response = await client.get(
        "/api/v1/connections/live_topo1/topology?include_services=true",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert mock_connection.get_hosts_services_batch.await_count == 1
    assert mock_connection.get_host_services.await_count == 0
    nodes = response.json()
    by_name = {n["name"]: n for n in nodes}
    assert [s["name"] for s in by_name["h1"]["services"]] == ["cpu"]
    assert by_name["h2"]["services"] == []
    assert [s["name"] for s in by_name["h3"]["services"]] == ["mem"]


@pytest.mark.asyncio
async def test_topology_truncates_and_sorts_services(
    client, admin_token, mock_connection, monkeypatch
):
    """services_per_host caps the list, non-OK first; truncated count is reported."""
    monkeypatch.setitem(state_service._connections, "live_topo2", mock_connection)
    mock_connection.get_topology.return_value = [_topology_row("h1")]
    mock_connection.get_hosts_services_batch.return_value = {
        "h1": [{"name": f"svc-ok-{i:02d}", "state": "OK", "output": ""} for i in range(10)]
        + [
            {"name": "alpha-warn", "state": "WARNING", "output": "high"},
            {"name": "beta-crit", "state": "CRITICAL", "output": "down"},
        ],
    }

    response = await client.get(
        "/api/v1/connections/live_topo2/topology?include_services=true&services_per_host=3",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    node = response.json()[0]
    names = [s["name"] for s in node["services"]]
    # Critical sorts before warning; OK fills the remaining slot alphabetically.
    assert names[0] == "beta-crit"
    assert names[1] == "alpha-warn"
    assert names[2] == "svc-ok-00"
    assert node["services_truncated_count"] == 12 - 3


@pytest.mark.asyncio
async def test_topology_caches_within_ttl(client, admin_token, mock_connection, monkeypatch):
    monkeypatch.setitem(state_service._connections, "live_topo3", mock_connection)
    mock_connection.get_topology.return_value = [_topology_row("h1")]
    mock_connection.get_hosts_services_batch.return_value = {"h1": []}

    headers = {"Authorization": f"Bearer {admin_token}"}
    url = "/api/v1/connections/live_topo3/topology?include_services=true"
    r1 = await client.get(url, headers=headers)
    r2 = await client.get(url, headers=headers)
    assert r1.status_code == 200
    assert r2.status_code == 200
    # Second call within TTL is served from cache.
    assert mock_connection.get_topology.await_count == 1
    assert mock_connection.get_hosts_services_batch.await_count == 1


@pytest.mark.asyncio
async def test_topology_top_k_skips_unaffected_hosts(
    client, admin_token, mock_connection, monkeypatch
):
    """Outside the top-K affected hosts: services_omitted=True, no bulk fetch."""
    monkeypatch.setitem(state_service._connections, "live_topo4", mock_connection)

    def row_with_summary(name: str, *, crit: int = 0, warn: int = 0) -> dict:
        return {
            "name": name,
            "parents": [],
            "state": "UP",
            "output": "ok",
            "services_summary": ServicesSummary(
                ok=0, warning=warn, critical=crit, unknown=0, pending=0
            ),
        }

    mock_connection.get_topology.return_value = [
        row_with_summary("h-clean-1"),
        row_with_summary("h-clean-2"),
        row_with_summary("h-clean-3"),
        row_with_summary("h-warn", warn=2),
        row_with_summary("h-crit", crit=5),
    ]
    mock_connection.get_hosts_services_batch.return_value = {
        "h-warn": [{"name": "svc", "state": "WARNING", "output": ""}],
        "h-crit": [{"name": "svc", "state": "CRITICAL", "output": ""}],
    }

    response = await client.get(
        "/api/v1/connections/live_topo4/topology?include_services=true&top_affected_hosts=2",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert mock_connection.get_hosts_services_batch.await_count == 1
    bulk_arg = sorted(mock_connection.get_hosts_services_batch.await_args.args[0])
    assert bulk_arg == ["h-crit", "h-warn"]

    by_name = {n["name"]: n for n in response.json()}
    assert by_name["h-crit"]["services_omitted"] is False
    assert by_name["h-warn"]["services_omitted"] is False
    for clean in ("h-clean-1", "h-clean-2", "h-clean-3"):
        assert by_name[clean]["services_omitted"] is True
        assert by_name[clean]["services"] == []


@pytest.mark.asyncio
async def test_topology_lock_dropped_on_failure(client, admin_token, mock_connection, monkeypatch):
    """Failed queries must not leave dangling entries in the lock dict.

    Otherwise repeated timeouts grow _topology_cache_locks without bound
    until the cache itself overflows and triggers eviction.
    """
    monkeypatch.setitem(state_service._connections, "live_topo_lock", mock_connection)
    connections_api._topology_cache.clear()
    connections_api._topology_cache_locks.clear()

    mock_connection.get_topology.side_effect = TimeoutError("livestatus timed out")
    with pytest.raises(TimeoutError):
        await client.get(
            "/api/v1/connections/live_topo_lock/topology?include_services=true",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
    assert connections_api._topology_cache_locks == {}


@pytest.mark.asyncio
async def test_topology_top_k_zero_skips_bulk_fetch(
    client, admin_token, mock_connection, monkeypatch
):
    """top_affected_hosts=0 must omit all service bulk fetches.

    Previously this fell into the "no top-K, fetch all" branch and could
    issue a 500-host OR-filter query against livestatus on large sites.
    """
    monkeypatch.setitem(state_service._connections, "live_topo5", mock_connection)
    mock_connection.get_topology.return_value = [
        {"name": f"h-{i}", "parents": [], "state": "UP", "output": "ok"} for i in range(3)
    ]
    response = await client.get(
        "/api/v1/connections/live_topo5/topology?include_services=true&top_affected_hosts=0",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    mock_connection.get_hosts_services_batch.assert_not_awaited()
    for n in response.json():
        assert n["services_omitted"] is True
        assert n["services"] == []


def _attach_with_auth_user(mock_connection: MagicMock) -> MagicMock:
    """Wire an async-context-manager ``with_auth_user`` onto a mock connection.

    The mock returned can be inspected via ``.assert_called_with(...)`` on the
    returned MagicMock to verify which auth-user the endpoint passes.
    """
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=None)
    ctx.__aexit__ = AsyncMock(return_value=None)
    holder = MagicMock(return_value=ctx)
    mock_connection.with_auth_user = holder
    return holder


@pytest.mark.asyncio
async def test_topology_scopes_to_caller_auth_user(
    client, regular_user, mock_connection, monkeypatch
):
    """Non-admin caller's contact-group filter must be applied via ``with_auth_user``."""
    monkeypatch.setitem(state_service._connections, "live_topo_auth", mock_connection)
    monkeypatch.setattr("app.core.config.settings.checkmk_omd_root", "/tmp/dummy")  # nosec B108
    # Disable the see_all bypass so the regular user actually gets scoped.
    monkeypatch.setattr(
        "app.api.v1.deps.cmk_integration.check_checkmk_permission",
        lambda *_a, **_k: False,
    )
    mock_connection.get_topology.return_value = [_topology_row("h1")]
    holder = _attach_with_auth_user(mock_connection)

    login = await client.post(
        "/api/v1/auth/login", json={"username": "regular", "password": "secret"}
    )
    token = login.json()["access_token"]

    response = await client.get(
        "/api/v1/connections/live_topo_auth/topology",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    holder.assert_called_once_with(regular_user.name)


@pytest.mark.asyncio
async def test_topology_admin_bypasses_auth_user_scope(
    client, admin_token, mock_connection, monkeypatch
):
    """Admins must NOT be wrapped in ``with_auth_user`` — they see everything."""
    monkeypatch.setitem(state_service._connections, "live_topo_admin", mock_connection)
    monkeypatch.setattr("app.core.config.settings.checkmk_omd_root", "/tmp/dummy")  # nosec B108
    mock_connection.get_topology.return_value = [_topology_row("h1")]
    holder = _attach_with_auth_user(mock_connection)

    response = await client.get(
        "/api/v1/connections/live_topo_admin/topology",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    holder.assert_not_called()


@pytest.mark.asyncio
async def test_topology_cache_isolated_per_auth_user(
    client, admin_token, regular_user, mock_connection, monkeypatch
):
    """Cache must not let a non-admin's restricted view leak into an admin's
    response (or vice versa) — the cache key includes auth_user."""
    monkeypatch.setitem(state_service._connections, "live_topo_iso", mock_connection)
    monkeypatch.setattr("app.core.config.settings.checkmk_omd_root", "/tmp/dummy")  # nosec B108
    monkeypatch.setattr(
        "app.api.v1.deps.cmk_integration.check_checkmk_permission",
        lambda *_a, **_k: False,
    )
    mock_connection.get_topology.return_value = [_topology_row("h1")]
    _attach_with_auth_user(mock_connection)

    login = await client.post(
        "/api/v1/auth/login", json={"username": "regular", "password": "secret"}
    )
    user_token = login.json()["access_token"]

    url = "/api/v1/connections/live_topo_iso/topology"
    r_admin = await client.get(url, headers={"Authorization": f"Bearer {admin_token}"})
    r_user = await client.get(url, headers={"Authorization": f"Bearer {user_token}"})
    assert r_admin.status_code == 200
    assert r_user.status_code == 200
    # Two distinct auth-user cache keys → two upstream fetches.
    assert mock_connection.get_topology.await_count == 2
