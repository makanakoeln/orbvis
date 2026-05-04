"""Tests for board object sub-resource endpoints and is_valid_image."""

from __future__ import annotations

import pytest

from app.core.image_security import is_valid_image as _is_valid_image


def _patch(monkeypatch, tmp_path):
    monkeypatch.setattr("app.core.config.settings.boards_dir", str(tmp_path))
    monkeypatch.setattr("app.services.board_service.settings.boards_dir", str(tmp_path))
    monkeypatch.setattr("app.api.v1.boards.settings.boards_dir", str(tmp_path))


async def _create_board(client, token, name="testboard"):
    return await client.post(
        "/api/v1/boards",
        json={"name": name, "alias": "Test"},
        headers={"Authorization": f"Bearer {token}"},
    )


# ---------------------------------------------------------------------------
# is_valid_image — pure unit tests
# ---------------------------------------------------------------------------


def test_is_valid_image_png():
    data = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
    assert _is_valid_image(data)


def test_is_valid_image_jpeg():
    data = b"\xff\xd8\xff\xe0" + b"\x00" * 100
    assert _is_valid_image(data)


def test_is_valid_image_gif87():
    data = b"GIF87a" + b"\x00" * 100
    assert _is_valid_image(data)


def test_is_valid_image_gif89():
    data = b"GIF89a" + b"\x00" * 100
    assert _is_valid_image(data)


def test_is_valid_image_webp():
    data = b"RIFF\x00\x00\x00\x00WEBP" + b"\x00" * 100
    assert _is_valid_image(data)


def test_is_valid_image_svg():
    data = b"<svg xmlns='http://www.w3.org/2000/svg'></svg>"
    assert _is_valid_image(data)


def test_is_valid_image_random_bytes():
    data = b"\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f"
    assert not _is_valid_image(data)


def test_is_valid_image_xml_without_svg():
    data = b"<?xml version='1.0' encoding='UTF-8'?><root></root>"
    assert not _is_valid_image(data)


def test_is_valid_image_rejects_svg_with_external_entity():
    """An SVG-looking document that references an external entity must be rejected."""
    data = (
        b'<?xml version="1.0"?>'
        b'<!DOCTYPE svg [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>'
        b'<svg xmlns="http://www.w3.org/2000/svg">&xxe;</svg>'
    )
    assert not _is_valid_image(data)


def test_is_valid_image_rejects_svg_with_dtd():
    """DTDs inside SVG are rejected by defusedxml."""
    data = (
        b'<?xml version="1.0"?>'
        b'<!DOCTYPE svg SYSTEM "attacker://payload">'
        b'<svg xmlns="http://www.w3.org/2000/svg"/>'
    )
    assert not _is_valid_image(data)


def test_is_valid_image_rejects_svg_with_broken_xml():
    data = b'<svg xmlns="http://www.w3.org/2000/svg"><g'
    assert not _is_valid_image(data)


# ---------------------------------------------------------------------------
# POST /boards/{name}/objects
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_add_object_to_board(client, admin_token, tmp_path, monkeypatch):
    _patch(monkeypatch, tmp_path)
    await _create_board(client, admin_token)

    response = await client.post(
        "/api/v1/boards/testboard/objects",
        json={
            "id": "host_1",
            "type": "host",
            "x": 100,
            "y": 200,
            "host_name": "server1",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 201
    objects = response.json()["objects"]
    assert any(o["id"] == "host_1" for o in objects)


@pytest.mark.asyncio
async def test_add_object_board_not_found(client, admin_token, tmp_path, monkeypatch):
    _patch(monkeypatch, tmp_path)
    response = await client.post(
        "/api/v1/boards/nonexistent/objects",
        json={"id": "host_1", "type": "host", "x": 0, "y": 0},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_add_object_duplicate_id(client, admin_token, tmp_path, monkeypatch):
    _patch(monkeypatch, tmp_path)
    await _create_board(client, admin_token)

    obj = {"id": "host_dup", "type": "host", "x": 0, "y": 0}
    await client.post(
        "/api/v1/boards/testboard/objects",
        json=obj,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    response = await client.post(
        "/api/v1/boards/testboard/objects",
        json=obj,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 409


# ---------------------------------------------------------------------------
# PUT /boards/{name}/objects/{obj_id}
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_object(client, admin_token, tmp_path, monkeypatch):
    _patch(monkeypatch, tmp_path)
    await _create_board(client, admin_token)
    await client.post(
        "/api/v1/boards/testboard/objects",
        json={"id": "host_2", "type": "host", "x": 0, "y": 0},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    response = await client.put(
        "/api/v1/boards/testboard/objects/host_2",
        json={"x": 99, "y": 88},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["x"] == 99
    assert response.json()["y"] == 88


@pytest.mark.asyncio
async def test_update_object_not_found(client, admin_token, tmp_path, monkeypatch):
    _patch(monkeypatch, tmp_path)
    await _create_board(client, admin_token)

    response = await client.put(
        "/api/v1/boards/testboard/objects/nonexistent",
        json={"x": 10},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
@pytest.mark.parametrize("field", ["hover_template", "context_template", "hover_url"])
async def test_non_admin_cannot_set_template_or_hover_url(
    client, admin_token, regular_token, regular_user, tmp_path, monkeypatch, field
):
    """hover_template / context_template / hover_url render in other users'
    sessions; only admins may set them. Editor-permission alone is not enough."""
    _patch(monkeypatch, tmp_path)
    await _create_board(client, admin_token)
    await client.post(
        "/api/v1/boards/testboard/objects",
        json={"id": "host_x", "type": "host", "x": 0, "y": 0},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    payload = {field: "<script>alert(1)</script>" if field != "hover_url" else "https://x"}
    response = await client.put(
        "/api/v1/boards/testboard/objects/host_x",
        json=payload,
        headers={"Authorization": f"Bearer {regular_token}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_can_set_hover_template(client, admin_token, tmp_path, monkeypatch):
    _patch(monkeypatch, tmp_path)
    await _create_board(client, admin_token)
    await client.post(
        "/api/v1/boards/testboard/objects",
        json={"id": "host_y", "type": "host", "x": 0, "y": 0},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    response = await client.put(
        "/api/v1/boards/testboard/objects/host_y",
        json={"hover_template": "<b>Hello</b>"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["hover_template"] == "<b>Hello</b>"


@pytest.mark.asyncio
async def test_update_object_rejects_javascript_url(client, admin_token, tmp_path, monkeypatch):
    _patch(monkeypatch, tmp_path)
    await _create_board(client, admin_token)
    await client.post(
        "/api/v1/boards/testboard/objects",
        json={"id": "host_z", "type": "host", "x": 0, "y": 0},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    response = await client.put(
        "/api/v1/boards/testboard/objects/host_z",
        json={"url": "javascript:alert(document.cookie)"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# DELETE /boards/{name}/objects/{obj_id}
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_object(client, admin_token, tmp_path, monkeypatch):
    _patch(monkeypatch, tmp_path)
    await _create_board(client, admin_token)
    await client.post(
        "/api/v1/boards/testboard/objects",
        json={"id": "host_3", "type": "host", "x": 0, "y": 0},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    response = await client.delete(
        "/api/v1/boards/testboard/objects/host_3",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_delete_object_not_found(client, admin_token, tmp_path, monkeypatch):
    _patch(monkeypatch, tmp_path)
    await _create_board(client, admin_token)

    response = await client.delete(
        "/api/v1/boards/testboard/objects/ghost",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 404
