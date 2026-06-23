#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Register Checkmk Maps permissions"""

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

from ._maps import load_map_summaries


def register(
    permission_section_registry: PermissionSectionRegistry,
    permission_registry: PermissionRegistry,
) -> None:
    permission_section_registry.register(PERMISSION_SECTION_ORBVIS)
    permission_registry.register(PermissionUse)
    permission_registry.register(PermissionViewAll)
    permission_registry.register(PermissionEditAll)
    permission_registry.register(PermissionConfigure)
    declare_dynamic_permissions(declare_map_permissions)


PERMISSION_SECTION_ORBVIS = PermissionSection(
    name="orbvis",
    title=_("Maps"),
    sort_index=75,
)


PermissionUse = Permission(
    section=PERMISSION_SECTION_ORBVIS,
    name="use",
    title=_l("Use Maps"),
    description=_l("Allows the user to access Checkmk Maps at all."),
    defaults=["admin", "user"],
)

PermissionViewAll = Permission(
    section=PERMISSION_SECTION_ORBVIS,
    name="view_all",
    title=_l("View all maps"),
    description=_l("Grants read access to all maps."),
    defaults=["admin", "user"],
)

PermissionEditAll = Permission(
    section=PERMISSION_SECTION_ORBVIS,
    name="edit_all",
    title=_l("Edit all maps"),
    description=_l(
        "Grants write access to all maps. Allows creating, modifying and deleting maps."
    ),
    defaults=["admin"],
)

PermissionConfigure = Permission(
    section=PERMISSION_SECTION_ORBVIS,
    name="configure",
    title=_l("Configure Maps"),
    description=_l("Grants access to the Maps general settings, connections and images."),
    defaults=["admin"],
)


_declared_map_permissions: set[str] = set()


def declare_map_permissions() -> None:
    """Declare per-map view and edit permissions dynamically.

    Maps are created, renamed and deleted at runtime through the Maps backend.
    Permissions declared by a previous call are unregistered first, so deleted
    maps disappear from the role & permission configuration without a restart.
    """
    for permission_name in _declared_map_permissions:
        permission_registry.unregister(permission_name)
    _declared_map_permissions.clear()

    for map_ in load_map_summaries():
        view_name = f"orbvis.view_{map_.name}"
        edit_name = f"orbvis.edit_{map_.name}"
        declare_permission(
            view_name,
            _("View map '%s'") % map_.alias,
            _("Grants read access to the map '%s'.") % map_.alias,
            ["admin", "user"],
        )
        declare_permission(
            edit_name,
            _("Edit map '%s'") % map_.alias,
            _("Grants write access to the map '%s'.") % map_.alias,
            ["admin"],
        )
        _declared_map_permissions.add(view_name)
        _declared_map_permissions.add(edit_name)
