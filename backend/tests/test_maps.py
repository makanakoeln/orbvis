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


def _patch(monkeypatch, tmp_path):
    monkeypatch.setattr("app.core.config.settings.maps_dir", str(tmp_path))
    monkeypatch.setattr("app.services.map_service.settings.maps_dir", str(tmp_path))
    monkeypatch.setattr("app.api.v1.maps.settings.maps_dir", str(tmp_path))


async def _create(client, token, tmp_path, monkeypatch, name="src-map"):
    _patch(monkeypatch, tmp_path)
    await client.post(
        "/api/v1/maps",
        json={"name": name, "alias": "Source"},
        headers={"Authorization": f"Bearer {token}"},
    )


# ---- Clone ----

@pytest.mark.asyncio
async def test_clone_map(client, admin_token, tmp_path, monkeypatch):
    await _create(client, admin_token, tmp_path, monkeypatch)

    resp = await client.post(
        "/api/v1/maps/src-map/clone",
        json={"new_name": "clone-map", "alias": "Cloned"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "clone-map"
    assert data["globals"]["alias"] == "Cloned"


@pytest.mark.asyncio
async def test_clone_map_conflict(client, admin_token, tmp_path, monkeypatch):
    await _create(client, admin_token, tmp_path, monkeypatch)
    # Create destination first
    await client.post(
        "/api/v1/maps",
        json={"name": "existing"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    resp = await client.post(
        "/api/v1/maps/src-map/clone",
        json={"new_name": "existing"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_clone_nonexistent_map(client, admin_token, tmp_path, monkeypatch):
    _patch(monkeypatch, tmp_path)
    resp = await client.post(
        "/api/v1/maps/ghost/clone",
        json={"new_name": "anything"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 404


# ---- Import / Export ----

@pytest.mark.asyncio
async def test_import_map(client, admin_token, tmp_path, monkeypatch):
    _patch(monkeypatch, tmp_path)
    payload = {
        "name": "imported",
        "globals": {"alias": "Imported", "backend_id": "test"},
        "objects": [],
    }
    resp = await client.post(
        "/api/v1/maps/import",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    assert resp.json()["name"] == "imported"


@pytest.mark.asyncio
async def test_import_map_conflict(client, admin_token, tmp_path, monkeypatch):
    await _create(client, admin_token, tmp_path, monkeypatch, "dup-map")
    payload = {"name": "dup-map", "globals": {}, "objects": []}
    resp = await client.post(
        "/api/v1/maps/import",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_import_map_overwrite(client, admin_token, tmp_path, monkeypatch):
    await _create(client, admin_token, tmp_path, monkeypatch, "over-map")
    payload = {"name": "over-map", "globals": {"alias": "Updated"}, "objects": []}
    resp = await client.post(
        "/api/v1/maps/import?overwrite=true",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    assert resp.json()["globals"]["alias"] == "Updated"


# ---- Background delete ----

@pytest.mark.asyncio
async def test_delete_background(client, admin_token, tmp_path, monkeypatch):
    await _create(client, admin_token, tmp_path, monkeypatch)

    # Write a fake background file
    bg_dir = tmp_path / "backgrounds"
    bg_dir.mkdir(parents=True, exist_ok=True)
    bg_file = bg_dir / "src-map.png"
    bg_file.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)  # fake PNG magic

    # Manually set background_image in the map
    from app.services import map_service
    from app.schemas.map import MapUpdate
    map_service.update_map("src-map", MapUpdate(background_image="src-map.png"))

    resp = await client.delete(
        "/api/v1/maps/src-map/background",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 204
    assert not bg_file.exists()

    # background_image should be cleared
    get_resp = await client.get(
        "/api/v1/maps/src-map",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert get_resp.json()["globals"]["background_image"] is None
