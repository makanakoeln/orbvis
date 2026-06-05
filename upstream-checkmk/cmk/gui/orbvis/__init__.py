#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.permissions import PermissionRegistry, PermissionSectionRegistry
from cmk.gui.sidebar._snapin._registry import SnapinRegistry

from . import _orbvis_auth
from ._orbvis_maps import OrbVisBoards


def register(
    permission_section_registry: PermissionSectionRegistry,
    permission_registry: PermissionRegistry,
    snapin_registry_: SnapinRegistry,
) -> None:
    _orbvis_auth.register(permission_section_registry, permission_registry)
    snapin_registry_.register(OrbVisBoards)
