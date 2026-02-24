"""Map API tests."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_list_maps_empty(client, admin_token, tmp_path, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.maps_dir", str(tmp_path))
    response = await client.get(
        "/api/v1/maps", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_create_and_get_map(client, admin_token, tmp_path, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.maps_dir", str(tmp_path))
    monkeypatch.setattr("app.services.map_service.settings.maps_dir", str(tmp_path))

    create_response = await client.post(
        "/api/v1/maps",
        json={"name": "test-map", "alias": "Test Map"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert create_response.status_code == 201
    data = create_response.json()
    assert data["name"] == "test-map"

    get_response = await client.get(
        "/api/v1/maps/test-map",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert get_response.status_code == 200
    assert get_response.json()["name"] == "test-map"


@pytest.mark.asyncio
async def test_get_nonexistent_map(client, admin_token):
    response = await client.get(
        "/api/v1/maps/does-not-exist",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 404
