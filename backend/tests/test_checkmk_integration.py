"""Tests for the file-based fallback paths of the Checkmk integration.

The test environment has no OMD site, so ``available`` is False and every
code path under test must work via direct .mk file parsing.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.integrations import checkmk
from app.integrations.checkmk import (
    FolderScope,
    _load_user_fallback,
    check_board_permission,
    check_checkmk_permission,
    check_configure_permission,
    check_create_permission,
    exec_mk_file,
    get_monitoring_core,
    get_user_contact_groups,
    load_user,
    load_user_inline_help,
    resolve_folder_scope,
)


@pytest.fixture(autouse=True)
def _standalone_cmk(monkeypatch):
    # Pin the no-cmk-imports environment and clear the roles.mk mtime cache,
    # which would otherwise leak between tests using different tmp_paths.
    monkeypatch.setattr(checkmk, "available", False)
    monkeypatch.setattr(checkmk, "_userdb_store_available", False)
    monkeypatch.setattr(checkmk, "_roles_cache", {})
    monkeypatch.setattr(checkmk, "_roles_cache_mtime", -1.0)


def _set_omd_root(monkeypatch, path: Path | str) -> None:
    monkeypatch.setattr("app.core.config.settings.checkmk_omd_root", str(path))


def _write_users_mk(omd_root: Path, users: dict[str, dict[str, object]]) -> None:
    wato_dir = omd_root / "etc" / "check_mk" / "multisite.d" / "wato"
    wato_dir.mkdir(parents=True, exist_ok=True)
    (wato_dir / "users.mk").write_text(f"multisite_users.update({users!r})\n", encoding="utf-8")


def _write_roles_mk(omd_root: Path, roles: dict[str, dict[str, object]]) -> None:
    wato_dir = omd_root / "etc" / "check_mk" / "multisite.d" / "wato"
    wato_dir.mkdir(parents=True, exist_ok=True)
    (wato_dir / "roles.mk").write_text(f"roles.update({roles!r})\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# FolderScope
# ---------------------------------------------------------------------------


def test_folder_scope_see_all_key_is_star():
    assert FolderScope(see_all=True).key == "*"


def test_folder_scope_key_sorts_groups():
    scope = FolderScope(see_all=False, groups=frozenset({"zeta", "alpha"}))
    assert scope.key == "cg:alpha,zeta"


def test_folder_scope_see_all_permits_anything():
    assert FolderScope(see_all=True).permits([]) is True
    assert FolderScope(see_all=True).permits(["whatever"]) is True


def test_folder_scope_permits_on_group_intersection():
    scope = FolderScope(see_all=False, groups=frozenset({"linux", "win"}))
    assert scope.permits(["linux", "other"]) is True
    assert scope.permits(["other"]) is False
    assert scope.permits([]) is False


# ---------------------------------------------------------------------------
# exec_mk_file
# ---------------------------------------------------------------------------


def test_exec_mk_file_parses_users_mk(tmp_path):
    mk = tmp_path / "users.mk"
    mk.write_text(
        "multisite_users.update({'alice': {'alias': 'Alice', 'roles': ['user']}})\n",
        encoding="utf-8",
    )
    ns = exec_mk_file(mk, {"multisite_users": {}})
    assert ns["multisite_users"] == {"alice": {"alias": "Alice", "roles": ["user"]}}


def test_exec_mk_file_missing_file_returns_defaults():
    ns = exec_mk_file(Path("/nonexistent/users.mk"), {"multisite_users": {"x": 1}})
    assert ns == {"multisite_users": {"x": 1}}


def test_exec_mk_file_does_not_mutate_defaults(tmp_path):
    mk = tmp_path / "users.mk"
    mk.write_text("multisite_users = {'bob': {}}\n", encoding="utf-8")
    defaults: dict[str, object] = {"multisite_users": {}}
    exec_mk_file(mk, defaults)
    assert defaults == {"multisite_users": {}}


def test_exec_mk_file_raises_on_syntax_error(tmp_path):
    # exec_mk_file itself propagates parse errors; the swallowing into a safe
    # default happens in its callers (see the _load_user_fallback test below).
    mk = tmp_path / "broken.mk"
    mk.write_text("this is { not python\n", encoding="utf-8")
    with pytest.raises(SyntaxError):
        exec_mk_file(mk, {"multisite_users": {}})


# ---------------------------------------------------------------------------
# get_monitoring_core
# ---------------------------------------------------------------------------


def test_get_monitoring_core_no_omd_root(monkeypatch):
    _set_omd_root(monkeypatch, "")
    assert get_monitoring_core() is None


def test_get_monitoring_core_missing_site_conf(tmp_path, monkeypatch):
    _set_omd_root(monkeypatch, tmp_path)
    assert get_monitoring_core() is None


@pytest.mark.parametrize("core", ["cmc", "nagios"])
def test_get_monitoring_core_reads_config_core(tmp_path, monkeypatch, core):
    _set_omd_root(monkeypatch, tmp_path)
    omd_dir = tmp_path / "etc" / "omd"
    omd_dir.mkdir(parents=True)
    (omd_dir / "site.conf").write_text(
        f"CONFIG_ADMIN_MAIL=''\nCONFIG_CORE='{core}'\n", encoding="utf-8"
    )
    assert get_monitoring_core() == core


def test_get_monitoring_core_unknown_value_returns_none(tmp_path, monkeypatch):
    _set_omd_root(monkeypatch, tmp_path)
    omd_dir = tmp_path / "etc" / "omd"
    omd_dir.mkdir(parents=True)
    (omd_dir / "site.conf").write_text("CONFIG_CORE='icinga'\n", encoding="utf-8")
    assert get_monitoring_core() is None


# ---------------------------------------------------------------------------
# _load_user_fallback
# ---------------------------------------------------------------------------


def test_load_user_fallback_reads_multisite_users(tmp_path, monkeypatch):
    _set_omd_root(monkeypatch, tmp_path)
    _write_users_mk(
        tmp_path,
        {"alice": {"alias": "Alice", "roles": ["admin"], "contactgroups": ["linux"]}},
    )
    data = _load_user_fallback("alice")
    assert data == {"alias": "Alice", "roles": ["admin"], "contactgroups": ["linux"]}


def test_load_user_fallback_unknown_user_returns_empty(tmp_path, monkeypatch):
    _set_omd_root(monkeypatch, tmp_path)
    _write_users_mk(tmp_path, {"alice": {"roles": ["user"]}})
    assert _load_user_fallback("nobody") == {}


def test_load_user_fallback_profile_mk_overrides_wato_data(tmp_path, monkeypatch):
    _set_omd_root(monkeypatch, tmp_path)
    _write_users_mk(tmp_path, {"alice": {"roles": ["user"], "ui_theme": "facelift"}})
    profile_dir = tmp_path / "var" / "check_mk" / "web" / "alice"
    profile_dir.mkdir(parents=True)
    (profile_dir / "ui_theme.mk").write_text("modern-dark\n", encoding="utf-8")
    (profile_dir / "language.mk").write_text("de", encoding="utf-8")
    data = _load_user_fallback("alice")
    assert data["ui_theme"] == "modern-dark"
    assert data["language"] == "de"
    assert data["roles"] == ["user"]


def test_load_user_fallback_empty_profile_file_does_not_override(tmp_path, monkeypatch):
    _set_omd_root(monkeypatch, tmp_path)
    _write_users_mk(tmp_path, {"alice": {"ui_theme": "facelift"}})
    profile_dir = tmp_path / "var" / "check_mk" / "web" / "alice"
    profile_dir.mkdir(parents=True)
    (profile_dir / "ui_theme.mk").write_text("   \n", encoding="utf-8")
    assert _load_user_fallback("alice")["ui_theme"] == "facelift"


def test_load_user_fallback_broken_users_mk_returns_empty(tmp_path, monkeypatch):
    _set_omd_root(monkeypatch, tmp_path)
    wato_dir = tmp_path / "etc" / "check_mk" / "multisite.d" / "wato"
    wato_dir.mkdir(parents=True)
    (wato_dir / "users.mk").write_text("multisite_users = { broken\n", encoding="utf-8")
    assert _load_user_fallback("alice") == {}


# ---------------------------------------------------------------------------
# load_user
# ---------------------------------------------------------------------------


def test_load_user_no_omd_root_returns_empty(monkeypatch):
    _set_omd_root(monkeypatch, "")
    assert load_user("alice") == {}


def test_load_user_uses_file_fallback_when_cmk_unavailable(tmp_path, monkeypatch):
    _set_omd_root(monkeypatch, tmp_path)
    _write_users_mk(tmp_path, {"alice": {"alias": "Alice", "roles": ["user"]}})
    assert load_user("alice") == {"alias": "Alice", "roles": ["user"]}


def test_load_user_missing_users_mk_returns_empty(tmp_path, monkeypatch):
    _set_omd_root(monkeypatch, tmp_path)
    assert load_user("alice") == {}


# ---------------------------------------------------------------------------
# check_checkmk_permission
# ---------------------------------------------------------------------------


def test_check_permission_no_omd_root(monkeypatch):
    _set_omd_root(monkeypatch, "")
    assert check_checkmk_permission("alice", "orbvis.use") is False


def test_check_permission_admin_defaults_without_roles_mk(tmp_path, monkeypatch):
    _set_omd_root(monkeypatch, tmp_path)
    _write_users_mk(tmp_path, {"alice": {"roles": ["admin"]}})
    assert check_checkmk_permission("alice", "orbvis.use") is True
    assert check_checkmk_permission("alice", "orbvis.configure") is True
    assert check_checkmk_permission("alice", "wato.see_all_folders") is True


def test_check_permission_user_role_defaults(tmp_path, monkeypatch):
    _set_omd_root(monkeypatch, tmp_path)
    _write_users_mk(tmp_path, {"bob": {"roles": ["user"]}})
    assert check_checkmk_permission("bob", "orbvis.use") is True
    assert check_checkmk_permission("bob", "orbvis.configure") is False
    assert check_checkmk_permission("bob", "wato.see_all_folders") is False
    assert check_checkmk_permission("bob", "action.acknowledge") is True
    assert check_checkmk_permission("bob", "action.notifications") is False


def test_check_permission_explicit_grant_in_roles_mk(tmp_path, monkeypatch):
    _set_omd_root(monkeypatch, tmp_path)
    _write_users_mk(tmp_path, {"guesty": {"roles": ["guest"]}})
    _write_roles_mk(tmp_path, {"guest": {"permissions": {"orbvis.use": True}}})
    assert check_checkmk_permission("guesty", "orbvis.use") is True


def test_check_permission_explicit_deny_overrides_default(tmp_path, monkeypatch):
    _set_omd_root(monkeypatch, tmp_path)
    _write_users_mk(tmp_path, {"bob": {"roles": ["user"]}})
    _write_roles_mk(tmp_path, {"user": {"permissions": {"orbvis.use": False}}})
    assert check_checkmk_permission("bob", "orbvis.use") is False


def test_check_permission_custom_role_inherits_basedon_defaults(tmp_path, monkeypatch):
    _set_omd_root(monkeypatch, tmp_path)
    _write_users_mk(tmp_path, {"carol": {"roles": ["superop"]}})
    _write_roles_mk(tmp_path, {"superop": {"basedon": "admin", "permissions": {}}})
    assert check_checkmk_permission("carol", "orbvis.configure") is True


def test_check_permission_per_board_defaults(tmp_path, monkeypatch):
    _set_omd_root(monkeypatch, tmp_path)
    _write_users_mk(tmp_path, {"bob": {"roles": ["user"]}})
    assert check_checkmk_permission("bob", "orbvis.view_myboard") is True
    assert check_checkmk_permission("bob", "orbvis.edit_myboard") is False


def test_check_permission_unknown_permission_is_denied(tmp_path, monkeypatch):
    _set_omd_root(monkeypatch, tmp_path)
    _write_users_mk(tmp_path, {"alice": {"roles": ["admin"]}})
    assert check_checkmk_permission("alice", "general.some_unknown_perm") is False


def test_check_permission_broken_roles_mk_falls_back_to_defaults(tmp_path, monkeypatch):
    _set_omd_root(monkeypatch, tmp_path)
    _write_users_mk(tmp_path, {"alice": {"roles": ["admin"]}})
    wato_dir = tmp_path / "etc" / "check_mk" / "multisite.d" / "wato"
    (wato_dir / "roles.mk").write_text("roles = { broken\n", encoding="utf-8")
    assert check_checkmk_permission("alice", "orbvis.use") is True


# ---------------------------------------------------------------------------
# check_board_permission / check_configure_permission / check_create_permission
# ---------------------------------------------------------------------------


def test_board_permission_no_omd_root(monkeypatch):
    _set_omd_root(monkeypatch, "")
    assert check_board_permission("alice", "b1", "view") is False
    assert check_board_permission("alice", "b1", "edit") is False


def test_board_permission_user_may_view_but_not_edit(tmp_path, monkeypatch):
    _set_omd_root(monkeypatch, tmp_path)
    _write_users_mk(tmp_path, {"bob": {"roles": ["user"]}})
    assert check_board_permission("bob", "b1", "view") is True
    assert check_board_permission("bob", "b1", "edit") is False


def test_board_permission_admin_may_edit(tmp_path, monkeypatch):
    _set_omd_root(monkeypatch, tmp_path)
    _write_users_mk(tmp_path, {"alice": {"roles": ["admin"]}})
    assert check_board_permission("alice", "b1", "edit") is True


def test_board_permission_per_board_edit_grant(tmp_path, monkeypatch):
    _set_omd_root(monkeypatch, tmp_path)
    _write_users_mk(tmp_path, {"bob": {"roles": ["user"]}})
    _write_roles_mk(tmp_path, {"user": {"permissions": {"orbvis.edit_b1": True}}})
    assert check_board_permission("bob", "b1", "edit") is True
    assert check_board_permission("bob", "other", "edit") is False


def test_board_permission_requires_orbvis_use(tmp_path, monkeypatch):
    _set_omd_root(monkeypatch, tmp_path)
    _write_users_mk(tmp_path, {"guesty": {"roles": ["guest"]}})
    _write_roles_mk(tmp_path, {"guest": {"permissions": {"orbvis.view_all": True}}})
    assert check_board_permission("guesty", "b1", "view") is False


def test_board_permission_unknown_action_is_denied(tmp_path, monkeypatch):
    _set_omd_root(monkeypatch, tmp_path)
    _write_users_mk(tmp_path, {"alice": {"roles": ["admin"]}})
    assert check_board_permission("alice", "b1", "delete") is False


def test_configure_permission(tmp_path, monkeypatch):
    _set_omd_root(monkeypatch, tmp_path)
    _write_users_mk(tmp_path, {"alice": {"roles": ["admin"]}, "bob": {"roles": ["user"]}})
    assert check_configure_permission("alice") is True
    assert check_configure_permission("bob") is False


def test_configure_permission_no_omd_root(monkeypatch):
    _set_omd_root(monkeypatch, "")
    assert check_configure_permission("alice") is False


def test_create_permission(tmp_path, monkeypatch):
    _set_omd_root(monkeypatch, tmp_path)
    _write_users_mk(tmp_path, {"alice": {"roles": ["admin"]}, "bob": {"roles": ["user"]}})
    assert check_create_permission("alice") is True
    assert check_create_permission("bob") is False


def test_create_permission_no_omd_root(monkeypatch):
    _set_omd_root(monkeypatch, "")
    assert check_create_permission("alice") is False


# ---------------------------------------------------------------------------
# get_user_contact_groups
# ---------------------------------------------------------------------------


def test_contact_groups_no_omd_root(monkeypatch):
    _set_omd_root(monkeypatch, "")
    assert get_user_contact_groups("alice") == []


def test_contact_groups_from_users_mk(tmp_path, monkeypatch):
    _set_omd_root(monkeypatch, tmp_path)
    _write_users_mk(tmp_path, {"alice": {"contactgroups": ["linux", "win"]}})
    assert get_user_contact_groups("alice") == ["linux", "win"]


def test_contact_groups_missing_attribute(tmp_path, monkeypatch):
    _set_omd_root(monkeypatch, tmp_path)
    _write_users_mk(tmp_path, {"alice": {"roles": ["user"]}})
    assert get_user_contact_groups("alice") == []


def test_contact_groups_non_list_value_ignored(tmp_path, monkeypatch):
    _set_omd_root(monkeypatch, tmp_path)
    _write_users_mk(tmp_path, {"alice": {"contactgroups": "linux"}})
    assert get_user_contact_groups("alice") == []


# ---------------------------------------------------------------------------
# load_user_inline_help
# ---------------------------------------------------------------------------


def test_load_user_inline_help_false_when_cmk_unavailable():
    assert load_user_inline_help("alice") is False


# ---------------------------------------------------------------------------
# resolve_folder_scope
# ---------------------------------------------------------------------------


def test_resolve_folder_scope_standalone_sees_all(monkeypatch):
    _set_omd_root(monkeypatch, "")
    assert resolve_folder_scope("alice", is_admin=False) == FolderScope(see_all=True)


def test_resolve_folder_scope_admin_flag_sees_all(tmp_path, monkeypatch):
    _set_omd_root(monkeypatch, tmp_path)
    _write_users_mk(tmp_path, {"alice": {"roles": ["user"]}})
    assert resolve_folder_scope("alice", is_admin=True).see_all is True


def test_resolve_folder_scope_admin_role_sees_all(tmp_path, monkeypatch):
    _set_omd_root(monkeypatch, tmp_path)
    _write_users_mk(tmp_path, {"alice": {"roles": ["admin"]}})
    assert resolve_folder_scope("alice", is_admin=False).see_all is True


def test_resolve_folder_scope_user_limited_to_contact_groups(tmp_path, monkeypatch):
    _set_omd_root(monkeypatch, tmp_path)
    _write_users_mk(tmp_path, {"bob": {"roles": ["user"], "contactgroups": ["linux"]}})
    scope = resolve_folder_scope("bob", is_admin=False)
    assert scope.see_all is False
    assert scope.groups == frozenset({"linux"})
    assert scope.permits(["linux"]) is True
    assert scope.permits(["win"]) is False


def test_resolve_folder_scope_user_without_groups_sees_nothing(tmp_path, monkeypatch):
    _set_omd_root(monkeypatch, tmp_path)
    _write_users_mk(tmp_path, {"bob": {"roles": ["user"]}})
    scope = resolve_folder_scope("bob", is_admin=False)
    assert scope.see_all is False
    assert scope.permits(["linux"]) is False
