"""Permission-gate characterization + spec tests.

Phase A (``TestStandaloneGates``) locks the *current* standalone behaviour so the
granular-permission refactor cannot accidentally open a gate that must stay
admin-only when no Checkmk is configured. These pass on HEAD.

Phase B (``TestCapabilityHelpers`` / ``TestCmkModeGates`` / ``TestMeCapabilities``)
specifies the *new* behaviour: in CMK mode the gates must honour ``orbvis.edit_all``
(create/delete boards) and ``orbvis.configure`` (connections / images / settings)
instead of the bare ``is_admin`` flag. These fail on HEAD and pass after the impl.
"""

from __future__ import annotations

import pytest

from app.api.v1.deps import (
    allowed_command_actions,
    can_configure,
    can_create_board,
    can_run_command,
)
from app.integrations.checkmk import _has_permission
from app.models.user import User


def _patch_boards_dir(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr("app.core.config.settings.boards_dir", str(tmp_path))
    monkeypatch.setattr("app.services.board_service.settings.boards_dir", str(tmp_path))
    monkeypatch.setattr("app.api.v1.boards.settings.boards_dir", str(tmp_path))


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Phase A — standalone characterization (green on HEAD)
# ---------------------------------------------------------------------------


class TestStandaloneGates:
    """Without Checkmk, every admin-only write gate must reject a plain user."""

    @pytest.mark.asyncio
    async def test_regular_cannot_create_board(
        self, client, regular_token, regular_user, tmp_path, monkeypatch
    ):
        _patch_boards_dir(monkeypatch, tmp_path)
        resp = await client.post(
            "/api/v1/boards", json={"name": "x-board"}, headers=_auth(regular_token)
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_regular_cannot_bulk_delete_board(
        self, client, regular_token, regular_user, tmp_path, monkeypatch
    ):
        _patch_boards_dir(monkeypatch, tmp_path)
        resp = await client.post(
            "/api/v1/boards/bulk-delete",
            json={"names": ["whatever"]},
            headers=_auth(regular_token),
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_regular_cannot_delete_board(
        self, client, regular_token, regular_user, tmp_path, monkeypatch
    ):
        _patch_boards_dir(monkeypatch, tmp_path)
        resp = await client.delete("/api/v1/boards/whatever", headers=_auth(regular_token))
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_regular_can_list_connection_objects(self, client, regular_token, regular_user):
        # The host/object autocomplete is intentionally NOT admin-only: any
        # authenticated user may query it (results are contact-group scoped in
        # CMK). An unknown connection yields an empty list, not a 403.
        resp = await client.get(
            "/api/v1/connections/some_conn/objects?type=host", headers=_auth(regular_token)
        )
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_regular_cannot_list_connection_folders(
        self, client, regular_token, regular_user
    ):
        # Folders stay configure-gated: the raw SETUP folder skeleton is not
        # contact-group scoped, so it must not leak to non-configure users.
        resp = await client.get(
            "/api/v1/connections/some_conn/folders", headers=_auth(regular_token)
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_regular_cannot_update_settings(self, client, regular_token, regular_user):
        resp = await client.put("/api/v1/settings", json={}, headers=_auth(regular_token))
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_regular_cannot_delete_image(self, client, regular_token, regular_user):
        resp = await client.delete("/api/v1/images/anything.png", headers=_auth(regular_token))
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_admin_can_create_board(self, client, admin_token, tmp_path, monkeypatch):
        _patch_boards_dir(monkeypatch, tmp_path)
        resp = await client.post(
            "/api/v1/boards", json={"name": "ok-board"}, headers=_auth(admin_token)
        )
        assert resp.status_code == 201

    @pytest.mark.asyncio
    async def test_regular_cannot_run_host_action(self, client, regular_token, regular_user):
        resp = await client.post(
            "/api/v1/connections/some_conn/host-action",
            json={"action": "acknowledge", "host_name": "h", "comment": "x"},
            headers=_auth(regular_token),
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_admin_host_action_passes_permission_gate(self, client, admin_token):
        # Permission gate is checked before the connection lookup, so an admin
        # gets past it and only trips on the missing connection (404, not 403).
        resp = await client.post(
            "/api/v1/connections/missing/host-action",
            json={"action": "acknowledge", "host_name": "h", "comment": "x"},
            headers=_auth(admin_token),
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Phase B — capability-helper spec (unit level)
# ---------------------------------------------------------------------------


class TestCapabilityHelpers:
    def test_standalone_admin_can_configure_and_create(self, monkeypatch):
        monkeypatch.setattr("app.api.v1.deps.settings.checkmk_omd_root", "")
        admin = User(user_id=1, name="admin", is_admin=True)
        assert can_configure(admin) is True
        assert can_create_board(admin) is True

    def test_standalone_regular_denied(self, monkeypatch):
        monkeypatch.setattr("app.api.v1.deps.settings.checkmk_omd_root", "")
        regular = User(user_id=2, name="regular", is_admin=False)
        assert can_configure(regular) is False
        assert can_create_board(regular) is False

    def test_cmk_configure_delegates_to_checkmk(self, monkeypatch):
        monkeypatch.setattr("app.api.v1.deps.settings.checkmk_omd_root", "/omd/sites/test")
        monkeypatch.setattr(
            "app.integrations.checkmk.check_configure_permission",
            lambda username: username == "configurer",
        )
        assert can_configure(User(user_id=3, name="configurer", is_admin=False)) is True
        assert can_configure(User(user_id=4, name="viewer", is_admin=False)) is False

    def test_cmk_create_delegates_to_checkmk(self, monkeypatch):
        monkeypatch.setattr("app.api.v1.deps.settings.checkmk_omd_root", "/omd/sites/test")
        monkeypatch.setattr(
            "app.integrations.checkmk.check_create_permission",
            lambda username: username == "editor",
        )
        assert can_create_board(User(user_id=5, name="editor", is_admin=False)) is True
        assert can_create_board(User(user_id=6, name="viewer", is_admin=False)) is False

    def test_cmk_admin_bypasses_permission_check(self, monkeypatch):
        monkeypatch.setattr("app.api.v1.deps.settings.checkmk_omd_root", "/omd/sites/test")
        monkeypatch.setattr(
            "app.integrations.checkmk.check_configure_permission", lambda username: False
        )
        monkeypatch.setattr(
            "app.integrations.checkmk.check_create_permission", lambda username: False
        )
        admin = User(user_id=7, name="cmkadmin", is_admin=True)
        assert can_configure(admin) is True
        assert can_create_board(admin) is True


class TestCommandPermissions:
    def test_standalone_only_admin_runs_commands(self, monkeypatch):
        monkeypatch.setattr("app.api.v1.deps.settings.checkmk_omd_root", "")
        admin = User(user_id=1, name="admin", is_admin=True)
        regular = User(user_id=2, name="regular", is_admin=False)
        assert can_run_command(admin, "acknowledge") is True
        assert can_run_command(regular, "acknowledge") is False
        assert allowed_command_actions(regular) == []

    def test_cmk_command_delegates_per_verb(self, monkeypatch):
        monkeypatch.setattr("app.api.v1.deps.settings.checkmk_omd_root", "/omd/sites/test")
        # User holds action.downtimes but not action.acknowledge.
        monkeypatch.setattr(
            "app.integrations.checkmk.check_checkmk_permission",
            lambda username, perm: perm == "action.downtimes",
        )
        user = User(user_id=3, name="noc", is_admin=False)
        assert can_run_command(user, "schedule_downtime") is True
        assert can_run_command(user, "remove_downtime") is True
        assert can_run_command(user, "acknowledge") is False
        assert allowed_command_actions(user) == ["schedule_downtime", "remove_downtime"]

    def test_unknown_verb_denied(self, monkeypatch):
        monkeypatch.setattr("app.api.v1.deps.settings.checkmk_omd_root", "")
        admin = User(user_id=4, name="admin", is_admin=True)
        assert can_run_command(admin, "self_destruct") is False

    def test_normal_monitoring_user_holds_command_defaults(self):
        # The reported bug: base role "user" must get action.downtimes/acknowledge
        # by default, while action.notifications is admin-only unless granted.
        user_data = {"roles": ["user"]}
        roles: dict[str, object] = {"user": {}}
        assert _has_permission(user_data, roles, "action.downtimes") is True
        assert _has_permission(user_data, roles, "action.acknowledge") is True
        assert _has_permission(user_data, roles, "action.notifications") is False


# ---------------------------------------------------------------------------
# Phase B — CMK-mode HTTP gates (non-admin with the right permission passes)
# ---------------------------------------------------------------------------


class TestCmkModeGates:
    @pytest.mark.asyncio
    async def test_cmk_editor_can_create_board(
        self, client, regular_token, regular_user, tmp_path, monkeypatch
    ):
        _patch_boards_dir(monkeypatch, tmp_path)
        monkeypatch.setattr("app.api.v1.deps.settings.checkmk_omd_root", "/omd/sites/test")
        monkeypatch.setattr(
            "app.integrations.checkmk.check_create_permission", lambda username: True
        )
        resp = await client.post(
            "/api/v1/boards", json={"name": "cmk-board"}, headers=_auth(regular_token)
        )
        assert resp.status_code == 201

    @pytest.mark.asyncio
    async def test_cmk_configurer_can_update_settings(
        self, client, regular_token, regular_user, tmp_path, monkeypatch
    ):
        boards_dir = tmp_path / "boards"
        boards_dir.mkdir(exist_ok=True)
        monkeypatch.setattr("app.core.config.settings.boards_dir", str(boards_dir))
        monkeypatch.setattr("app.services.settings_service.settings.boards_dir", str(boards_dir))
        monkeypatch.setattr("app.api.v1.deps.settings.checkmk_omd_root", "/omd/sites/test")
        monkeypatch.setattr(
            "app.integrations.checkmk.check_configure_permission", lambda username: True
        )
        resp = await client.put("/api/v1/settings", json={}, headers=_auth(regular_token))
        assert resp.status_code != 403

    @pytest.mark.asyncio
    async def test_cmk_board_creator_can_read_connection_list(
        self, client, regular_token, regular_user, monkeypatch
    ):
        # A board creator (edit_all) without configure must still read the
        # connection list to pick a connection when creating a board.
        monkeypatch.setattr("app.api.v1.deps.settings.checkmk_omd_root", "/omd/sites/test")
        monkeypatch.setattr(
            "app.integrations.checkmk.check_create_permission", lambda username: True
        )
        monkeypatch.setattr(
            "app.integrations.checkmk.check_configure_permission", lambda username: False
        )
        resp = await client.get("/api/v1/connections", headers=_auth(regular_token))
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_cmk_viewer_cannot_create_board(
        self, client, regular_token, regular_user, tmp_path, monkeypatch
    ):
        _patch_boards_dir(monkeypatch, tmp_path)
        monkeypatch.setattr("app.api.v1.deps.settings.checkmk_omd_root", "/omd/sites/test")
        monkeypatch.setattr(
            "app.integrations.checkmk.check_create_permission", lambda username: False
        )
        resp = await client.post(
            "/api/v1/boards", json={"name": "denied-board"}, headers=_auth(regular_token)
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Phase B — /me exposes capability flags for the frontend
# ---------------------------------------------------------------------------


class TestMeCapabilities:
    @pytest.mark.asyncio
    async def test_me_admin_has_all_capabilities(self, client, admin_token):
        resp = await client.get("/api/v1/auth/me", headers=_auth(admin_token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["can_configure"] is True
        assert data["can_create_boards"] is True
        assert "acknowledge" in data["command_permissions"]
        assert "schedule_downtime" in data["command_permissions"]

    @pytest.mark.asyncio
    async def test_me_regular_standalone_has_no_capabilities(
        self, client, regular_token, regular_user
    ):
        resp = await client.get("/api/v1/auth/me", headers=_auth(regular_token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["can_configure"] is False
        assert data["can_create_boards"] is False
        assert data["command_permissions"] == []
