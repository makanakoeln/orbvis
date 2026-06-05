#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Register general OrbVis permissions"""

from cmk.gui.i18n import _, _l
from cmk.gui.permissions import (
    declare_dynamic_permissions,
    declare_permission,
    Permission,
    permission_registry,
    PermissionRegistry,
    PermissionSection,
    PermissionSectionRegistry,
)

from ._boards import load_board_summaries


def register(
    permission_section_registry: PermissionSectionRegistry,
    permission_registry: PermissionRegistry,
) -> None:
    permission_section_registry.register(PERMISSION_SECTION_ORBVIS)
    permission_registry.register(PermissionUse)
    permission_registry.register(PermissionViewAll)
    permission_registry.register(PermissionEditAll)
    permission_registry.register(PermissionConfigure)
    declare_dynamic_permissions(declare_board_permissions)


PERMISSION_SECTION_ORBVIS = PermissionSection(
    name="orbvis",
    title=_("OrbVis"),
    sort_index=75,
)


PermissionUse = Permission(
    section=PERMISSION_SECTION_ORBVIS,
    name="use",
    title=_l("Use OrbVis"),
    description=_l("Allows the user to access OrbVis at all."),
    defaults=["admin", "user"],
)

PermissionViewAll = Permission(
    section=PERMISSION_SECTION_ORBVIS,
    name="view_all",
    title=_l("View all boards"),
    description=_l("Grants read access to all OrbVis boards."),
    defaults=["admin", "user"],
)

PermissionEditAll = Permission(
    section=PERMISSION_SECTION_ORBVIS,
    name="edit_all",
    title=_l("Edit all boards"),
    description=_l(
        "Grants write access to all OrbVis boards. Allows creating, modifying and deleting boards."
    ),
    defaults=["admin"],
)

PermissionConfigure = Permission(
    section=PERMISSION_SECTION_ORBVIS,
    name="configure",
    title=_l("Configure OrbVis"),
    description=_l("Grants access to OrbVis general settings, connections and images."),
    defaults=["admin"],
)


_declared_board_permissions: set[str] = set()


def declare_board_permissions() -> None:
    """Declare per-board view and edit permissions dynamically.

    Boards are created, renamed and deleted at runtime through the OrbVis
    backend. Permissions declared by a previous call are unregistered first,
    so deleted boards disappear from the role & permission configuration
    without a restart.
    """
    for permission_name in _declared_board_permissions:
        permission_registry.unregister(permission_name)
    _declared_board_permissions.clear()

    for board in load_board_summaries():
        view_name = f"orbvis.view_{board.name}"
        edit_name = f"orbvis.edit_{board.name}"
        declare_permission(
            view_name,
            _("View board '%s'") % board.alias,
            _("Grants read access to the OrbVis board '%s'.") % board.alias,
            ["admin", "user"],
        )
        declare_permission(
            edit_name,
            _("Edit board '%s'") % board.alias,
            _("Grants write access to the OrbVis board '%s'.") % board.alias,
            ["admin"],
        )
        _declared_board_permissions.add(view_name)
        _declared_board_permissions.add(edit_name)
