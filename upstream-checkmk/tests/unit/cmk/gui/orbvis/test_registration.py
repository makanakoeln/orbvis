#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

import cmk.gui.orbvis
import cmk.gui.sidebar._snapin._registry
from cmk.gui.orbvis import _orbvis_auth
from cmk.gui.orbvis._orbvis_maps import OrbVisBoards
from cmk.gui.permissions import PermissionRegistry, PermissionSectionRegistry
from cmk.gui.sidebar._snapin._registry import SnapinRegistry


def test_register(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(_orbvis_auth, "declare_dynamic_permissions", lambda func: None)
    monkeypatch.setattr(
        cmk.gui.sidebar._snapin._registry, "permission_registry", PermissionRegistry()
    )
    permission_section_registry = PermissionSectionRegistry()
    permission_registry = PermissionRegistry()
    snapin_registry = SnapinRegistry()

    cmk.gui.orbvis.register(permission_section_registry, permission_registry, snapin_registry)

    assert "orbvis" in permission_section_registry
    assert "orbvis.use" in permission_registry
    assert snapin_registry["orbvis_boards"] is OrbVisBoards
