"""Image library API tests."""

from __future__ import annotations

from pathlib import Path

import pytest

# A 1x1 transparent PNG that passes the magic-byte image check.
_PNG_BYTES = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000d49444154789c6300010000000500010d0a2db40000000049454e44ae426082"
)


def _patch_dirs(monkeypatch, tmp_path: Path) -> Path:
    """Point boards_dir at tmp_path; the images dir lives next to it."""
    boards = tmp_path / "boards"
    boards.mkdir()
    monkeypatch.setattr("app.core.config.settings.boards_dir", str(boards))
    monkeypatch.setattr("app.services.board_service.settings.boards_dir", str(boards))
    monkeypatch.setattr("app.api.v1.boards.settings.boards_dir", str(boards))
    monkeypatch.setattr("app.api.v1.images.settings.boards_dir", str(boards))
    images = tmp_path / "images"
    images.mkdir()
    return images


def _patch_builtin_dir(monkeypatch, builtins: Path) -> None:
    """Patch the built-in icon directory used to flag built-in images."""
    monkeypatch.setattr("app.api.v1.images._BUILTIN_DIR", builtins)


@pytest.mark.asyncio
async def test_list_marks_builtins(client, admin_token, tmp_path, monkeypatch):
    images_dir = _patch_dirs(monkeypatch, tmp_path)
    builtins = tmp_path / "builtin"
    builtins.mkdir()
    (builtins / "shipped.png").write_bytes(_PNG_BYTES)
    _patch_builtin_dir(monkeypatch, builtins)

    (images_dir / "shipped.png").write_bytes(_PNG_BYTES)
    (images_dir / "user.png").write_bytes(_PNG_BYTES)

    response = await client.get(
        "/api/v1/images", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    by_name = {entry["name"]: entry for entry in response.json()}
    assert by_name["shipped.png"]["builtin"] is True
    assert by_name["user.png"]["builtin"] is False


@pytest.mark.asyncio
async def test_delete_builtin_is_forbidden(client, admin_token, tmp_path, monkeypatch):
    images_dir = _patch_dirs(monkeypatch, tmp_path)
    builtins = tmp_path / "builtin"
    builtins.mkdir()
    (builtins / "shipped.png").write_bytes(_PNG_BYTES)
    _patch_builtin_dir(monkeypatch, builtins)
    (images_dir / "shipped.png").write_bytes(_PNG_BYTES)

    response = await client.delete(
        "/api/v1/images/shipped.png",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 403
    # File must still exist after a rejected delete.
    assert (images_dir / "shipped.png").exists()


@pytest.mark.asyncio
async def test_delete_in_use_returns_409_until_forced(client, admin_token, tmp_path, monkeypatch):
    images_dir = _patch_dirs(monkeypatch, tmp_path)
    _patch_builtin_dir(monkeypatch, tmp_path / "no-builtins")
    (images_dir / "icon.png").write_bytes(_PNG_BYTES)

    # Create a board that references the image as an object icon.
    create = await client.post(
        "/api/v1/boards",
        json={"name": "uses-icon", "alias": "Uses Icon"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert create.status_code == 201

    add_object = await client.post(
        "/api/v1/boards/uses-icon/objects",
        json={
            "id": "img1",
            "type": "image",
            "x": 10,
            "y": 10,
            "image_src": "icon.png",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert add_object.status_code in (200, 201), add_object.text

    # First attempt: server reports usage and refuses.
    blocked = await client.delete(
        "/api/v1/images/icon.png",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert blocked.status_code == 409
    detail = blocked.json()["detail"]
    assert detail["usage"][0]["board"] == "uses-icon"
    assert (images_dir / "icon.png").exists()

    # Forced delete succeeds.
    forced = await client.delete(
        "/api/v1/images/icon.png?force=true",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert forced.status_code == 204
    assert not (images_dir / "icon.png").exists()


@pytest.mark.asyncio
async def test_usage_endpoint_lists_referencing_boards(client, admin_token, tmp_path, monkeypatch):
    images_dir = _patch_dirs(monkeypatch, tmp_path)
    _patch_builtin_dir(monkeypatch, tmp_path / "no-builtins")
    (images_dir / "bg.png").write_bytes(_PNG_BYTES)

    await client.post(
        "/api/v1/boards",
        json={
            "name": "with-bg",
            "alias": "With BG",
            "background_image": "bg.png",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    usage = await client.get(
        "/api/v1/images/bg.png/usage",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert usage.status_code == 200
    body = usage.json()
    assert body[0]["board"] == "with-bg"
    assert body[0]["is_background"] is True


# ---------------------------------------------------------------------------
# Upload hardening: stem sanitisation, builtin protection, GIF rejection
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_upload_sanitizes_windows_path_stem(client, admin_token, tmp_path, monkeypatch):
    _patch_dirs(monkeypatch, tmp_path)
    resp = await client.post(
        "/api/v1/images",
        files={"file": (r"C:\Users\x\my icon.png", _PNG_BYTES, "image/png")},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    name = resp.json()["name"]
    assert "\\" not in name and "/" not in name and " " not in name
    # The sanitised name must be addressable by the delete endpoint.
    del_resp = await client.delete(
        f"/api/v1/images/{name}?force=true",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert del_resp.status_code == 204


@pytest.mark.asyncio
async def test_upload_cannot_overwrite_builtin(client, admin_token, tmp_path, monkeypatch):
    _patch_dirs(monkeypatch, tmp_path)
    builtin_dir = tmp_path / "builtin"
    builtin_dir.mkdir()
    (builtin_dir / "server.png").write_bytes(_PNG_BYTES)
    _patch_builtin_dir(monkeypatch, builtin_dir)
    resp = await client.post(
        "/api/v1/images",
        files={"file": ("server.png", _PNG_BYTES, "image/png")},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_upload_rejects_gif_with_faked_content_type(
    client, admin_token, tmp_path, monkeypatch
):
    _patch_dirs(monkeypatch, tmp_path)
    gif = b"GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
    resp = await client.post(
        "/api/v1/images",
        files={"file": ("anim.png", gif, "image/png")},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 415
