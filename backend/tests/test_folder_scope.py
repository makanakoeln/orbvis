"""FolderScope: SETUP-folder read visibility, distinct from monitoring scope."""

from app.integrations.checkmk import FolderScope, resolve_folder_scope


def test_see_all_permits_any_folder() -> None:
    scope = FolderScope(see_all=True)
    assert scope.permits([])
    assert scope.permits(["anything"])
    assert scope.key == "*"


def test_contact_group_scope_permits_only_shared_groups() -> None:
    scope = FolderScope(see_all=False, groups=frozenset({"team-a", "team-b"}))
    assert scope.permits(["team-a"])  # shares a group
    assert scope.permits(["x", "team-b"])
    assert not scope.permits(["team-c"])  # no overlap
    assert not scope.permits([])  # folder with no contact groups → admin-only
    assert scope.key == "cg:team-a,team-b"  # sorted + stable


def test_empty_scope_sees_no_restricted_folder() -> None:
    # A user with no contact groups (and no see-all) reads no scoped folders.
    scope = FolderScope(see_all=False, groups=frozenset())
    assert not scope.permits(["team-a"])
    assert scope.key == "cg:"


def test_resolve_folder_scope_standalone_sees_all() -> None:
    # No CHECKMK_OMD_ROOT in the test env → no folder ACLs → see all.
    scope = resolve_folder_scope("anyone", is_admin=False)
    assert scope.see_all
