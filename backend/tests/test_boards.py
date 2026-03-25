"""Board API tests."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_list_boards_empty(client, admin_token, tmp_path, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.boards_dir", str(tmp_path))
    response = await client.get(
        "/api/v1/boards", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_create_and_get_board(client, admin_token, tmp_path, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.boards_dir", str(tmp_path))
    monkeypatch.setattr("app.services.board_service.settings.boards_dir", str(tmp_path))

    create_response = await client.post(
        "/api/v1/boards",
        json={"name": "test-board", "alias": "Test Board"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert create_response.status_code == 201
    data = create_response.json()
    assert data["name"] == "test-board"

    get_response = await client.get(
        "/api/v1/boards/test-board",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert get_response.status_code == 200
    assert get_response.json()["name"] == "test-board"


@pytest.mark.asyncio
async def test_get_nonexistent_board(client, admin_token):
    response = await client.get(
        "/api/v1/boards/does-not-exist",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 404


def _patch(monkeypatch, tmp_path):
    monkeypatch.setattr("app.core.config.settings.boards_dir", str(tmp_path))
    monkeypatch.setattr("app.services.board_service.settings.boards_dir", str(tmp_path))
    monkeypatch.setattr("app.api.v1.boards.settings.boards_dir", str(tmp_path))


async def _create(client, token, tmp_path, monkeypatch, name="src-board"):
    _patch(monkeypatch, tmp_path)
    await client.post(
        "/api/v1/boards",
        json={"name": name, "alias": "Source"},
        headers={"Authorization": f"Bearer {token}"},
    )


# ---- Clone ----


@pytest.mark.asyncio
async def test_clone_board(client, admin_token, tmp_path, monkeypatch):
    await _create(client, admin_token, tmp_path, monkeypatch)

    resp = await client.post(
        "/api/v1/boards/src-board/clone",
        json={"new_name": "clone-board", "alias": "Cloned"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "clone-board"
    assert data["alias"] == "Cloned"


@pytest.mark.asyncio
async def test_clone_board_conflict(client, admin_token, tmp_path, monkeypatch):
    await _create(client, admin_token, tmp_path, monkeypatch)
    # Create destination first
    await client.post(
        "/api/v1/boards",
        json={"name": "existing"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    resp = await client.post(
        "/api/v1/boards/src-board/clone",
        json={"new_name": "existing"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_clone_nonexistent_board(client, admin_token, tmp_path, monkeypatch):
    _patch(monkeypatch, tmp_path)
    resp = await client.post(
        "/api/v1/boards/ghost/clone",
        json={"new_name": "anything"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 404


# ---- Import / Export ----


@pytest.mark.asyncio
async def test_import_board(client, admin_token, tmp_path, monkeypatch):
    _patch(monkeypatch, tmp_path)
    payload = {
        "name": "imported",
        "alias": "Imported",
        "backend_id": "test",
        "objects": [],
    }
    resp = await client.post(
        "/api/v1/boards/import",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    assert resp.json()["name"] == "imported"


@pytest.mark.asyncio
async def test_import_board_conflict(client, admin_token, tmp_path, monkeypatch):
    await _create(client, admin_token, tmp_path, monkeypatch, "dup-board")
    payload = {"name": "dup-board", "objects": []}
    resp = await client.post(
        "/api/v1/boards/import",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_import_board_overwrite(client, admin_token, tmp_path, monkeypatch):
    await _create(client, admin_token, tmp_path, monkeypatch, "over-board")
    payload = {"name": "over-board", "alias": "Updated", "objects": []}
    resp = await client.post(
        "/api/v1/boards/import?overwrite=true",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    assert resp.json()["alias"] == "Updated"


# ---- Background delete ----


@pytest.mark.asyncio
async def test_delete_background(client, admin_token, tmp_path, monkeypatch):
    await _create(client, admin_token, tmp_path, monkeypatch)

    # Write a fake background file
    bg_dir = tmp_path / "backgrounds"
    bg_dir.mkdir(parents=True, exist_ok=True)
    bg_file = bg_dir / "src-board.png"
    bg_file.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)  # fake PNG magic

    # Manually set background_image in the board
    from app.schemas.board import BoardUpdate
    from app.services import board_service

    board_service.update_board("src-board", BoardUpdate(background_image="src-board.png"))

    resp = await client.delete(
        "/api/v1/boards/src-board/background",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 204
    assert not bg_file.exists()

    # background_image should be cleared
    get_resp = await client.get(
        "/api/v1/boards/src-board",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert get_resp.json()["background_image"] is None
