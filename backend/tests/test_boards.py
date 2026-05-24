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


@pytest.mark.parametrize(
    "bad_name",
    [
        "../etc-passwd",  # path traversal attempt
        "foo bar",  # whitespace
        "foo/bar",  # slash
        "foo.bar",  # dot (could match board.mk filename tricks)
        "foo$",  # shell metacharacter
        "x" * 101,  # over length limit
    ],
)
@pytest.mark.asyncio
async def test_board_name_path_validation_rejects_unsafe(client, admin_token, bad_name):
    """The BoardName FastAPI path type must reject anything outside [A-Za-z0-9_-]{1,100}."""
    response = await client.get(
        f"/api/v1/boards/{bad_name}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    # FastAPI/Pydantic returns 422 for pattern / length violations, 404 for
    # slashes that hit a different route — either way no unsafe name reaches
    # the filesystem or permission lookup.
    assert response.status_code in (404, 422)


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


# ---- Bulk delete ----


@pytest.mark.asyncio
async def test_bulk_delete_mixed(client, admin_token, tmp_path, monkeypatch):
    _patch(monkeypatch, tmp_path)
    for n in ("alpha", "beta", "gamma"):
        await client.post(
            "/api/v1/boards",
            json={"name": n},
            headers={"Authorization": f"Bearer {admin_token}"},
        )

    resp = await client.post(
        "/api/v1/boards/bulk-delete",
        json={"names": ["alpha", "beta", "ghost", "alpha"]},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert sorted(body["deleted"]) == ["alpha", "beta"]
    assert len(body["failed"]) == 1
    assert body["failed"][0]["name"] == "ghost"
    assert "not found" in body["failed"][0]["reason"].lower()

    listing = await client.get("/api/v1/boards", headers={"Authorization": f"Bearer {admin_token}"})
    remaining = {b["name"] for b in listing.json()}
    assert remaining == {"gamma"}


@pytest.mark.asyncio
async def test_bulk_delete_rejects_empty(client, admin_token, tmp_path, monkeypatch):
    _patch(monkeypatch, tmp_path)
    resp = await client.post(
        "/api/v1/boards/bulk-delete",
        json={"names": []},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_bulk_delete_rejects_bad_name(client, admin_token, tmp_path, monkeypatch):
    _patch(monkeypatch, tmp_path)
    resp = await client.post(
        "/api/v1/boards/bulk-delete",
        json={"names": ["../etc/passwd"]},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 422


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
        "connection_id": "test",
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


_TINY_PNG = (
    b"\x89PNG\r\n\x1a\n"
    b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
    b"\x00\x00\x00\rIDATx\x9cc\xfc\xcf\xc0P\x0f\x00\x05\x01\x01\x02\xa0\xb5\xe1+\x00\x00\x00\x00IEND\xaeB`\x82"
)
_TINY_GIF = b"GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"


@pytest.mark.asyncio
async def test_upload_background_creates_file_and_sets_field(
    client, admin_token, tmp_path, monkeypatch
):
    from pathlib import Path

    await _create(client, admin_token, tmp_path, monkeypatch)
    resp = await client.post(
        "/api/v1/boards/src-board/background",
        files={"file": ("hero.png", _TINY_PNG, "image/png")},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["filename"] == "src-board.png"
    assert isinstance(body["version"], int)

    bg_path = Path(tmp_path) / "backgrounds" / "src-board.png"
    assert bg_path.exists()
    assert bg_path.read_bytes() == _TINY_PNG

    get_resp = await client.get(
        "/api/v1/boards/src-board",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert get_resp.json()["background_image"] == "src-board.png"


@pytest.mark.asyncio
async def test_upload_background_replaces_existing_with_different_format(
    client, admin_token, tmp_path, monkeypatch
):
    from pathlib import Path

    await _create(client, admin_token, tmp_path, monkeypatch)
    first = await client.post(
        "/api/v1/boards/src-board/background",
        files={"file": ("a.png", _TINY_PNG, "image/png")},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert first.status_code == 200
    png_path = Path(tmp_path) / "backgrounds" / "src-board.png"
    assert png_path.exists()

    second = await client.post(
        "/api/v1/boards/src-board/background",
        files={"file": ("b.gif", _TINY_GIF, "image/gif")},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert second.status_code == 200, second.text
    assert second.json()["filename"] == "src-board.gif"

    gif_path = Path(tmp_path) / "backgrounds" / "src-board.gif"
    assert gif_path.exists()
    assert gif_path.read_bytes() == _TINY_GIF
    get_resp = await client.get(
        "/api/v1/boards/src-board",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert get_resp.json()["background_image"] == "src-board.gif"
    assert not png_path.exists()


@pytest.mark.asyncio
async def test_upload_background_rejects_unsupported_mime(
    client, admin_token, tmp_path, monkeypatch
):
    await _create(client, admin_token, tmp_path, monkeypatch)
    resp = await client.post(
        "/api/v1/boards/src-board/background",
        files={"file": ("evil.exe", b"MZ\x90\x00binary", "application/octet-stream")},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 415


@pytest.mark.asyncio
async def test_upload_background_rejects_wrong_magic_bytes(
    client, admin_token, tmp_path, monkeypatch
):
    await _create(client, admin_token, tmp_path, monkeypatch)
    resp = await client.post(
        "/api/v1/boards/src-board/background",
        files={"file": ("fake.png", b"not a png at all", "image/png")},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 415


@pytest.mark.asyncio
async def test_upload_background_404_for_missing_board(client, admin_token, tmp_path, monkeypatch):
    _patch(monkeypatch, tmp_path)
    resp = await client.post(
        "/api/v1/boards/does-not-exist/background",
        files={"file": ("a.png", _TINY_PNG, "image/png")},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 404


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
    assert resp.status_code == 200
    assert isinstance(resp.json().get("version"), int)
    assert not bg_file.exists()

    # background_image should be cleared
    get_resp = await client.get(
        "/api/v1/boards/src-board",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert get_resp.json()["background_image"] is None


@pytest.mark.asyncio
async def test_update_board_increments_version(client, admin_token, tmp_path, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.boards_dir", str(tmp_path))
    monkeypatch.setattr("app.services.board_service.settings.boards_dir", str(tmp_path))

    await client.post(
        "/api/v1/boards",
        json={"name": "lock-board", "alias": "v0"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    initial = await client.get(
        "/api/v1/boards/lock-board", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert initial.json()["version"] == 0

    resp = await client.put(
        "/api/v1/boards/lock-board",
        json={"alias": "v1"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["version"] == 1


@pytest.mark.asyncio
async def test_update_board_rejects_stale_if_match(client, admin_token, tmp_path, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.boards_dir", str(tmp_path))
    monkeypatch.setattr("app.services.board_service.settings.boards_dir", str(tmp_path))

    await client.post(
        "/api/v1/boards",
        json={"name": "lock-board", "alias": "v0"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    # First operator saves successfully — bumps version to 1.
    await client.put(
        "/api/v1/boards/lock-board",
        json={"alias": "v1"},
        headers={
            "Authorization": f"Bearer {admin_token}",
            "If-Match": "0",
        },
    )

    # Second operator still holds version 0 → must be rejected.
    stale = await client.put(
        "/api/v1/boards/lock-board",
        json={"alias": "v2"},
        headers={
            "Authorization": f"Bearer {admin_token}",
            "If-Match": "0",
        },
    )
    assert stale.status_code == 409
    body = stale.json()
    assert body["detail"]["reason"] == "stale_board"
    assert body["detail"]["current_version"] == 1


@pytest.mark.asyncio
async def test_update_board_without_if_match_skips_check(
    client, admin_token, tmp_path, monkeypatch
):
    monkeypatch.setattr("app.core.config.settings.boards_dir", str(tmp_path))
    monkeypatch.setattr("app.services.board_service.settings.boards_dir", str(tmp_path))

    await client.post(
        "/api/v1/boards",
        json={"name": "lock-board", "alias": "v0"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    # Bump twice without supplying If-Match — both must succeed.
    for alias in ("v1", "v2"):
        resp = await client.put(
            "/api/v1/boards/lock-board",
            json={"alias": alias},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
    final = await client.get(
        "/api/v1/boards/lock-board", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert final.json()["version"] == 2
