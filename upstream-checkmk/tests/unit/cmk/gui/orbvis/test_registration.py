#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

import cmk.gui.orbvis
from cmk.gui.orbvis import _orbvis_auth
from cmk.gui.pages import PageRegistry
from cmk.gui.permissions import PermissionRegistry, PermissionSectionRegistry
from cmk.gui.watolib.main_menu import MainModuleRegistry, MainModuleTopicRegistry


def test_register(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(_orbvis_auth, "declare_dynamic_permissions", lambda _func: None)
    permission_section_registry = PermissionSectionRegistry()
    permission_registry = PermissionRegistry()
    page_registry = PageRegistry()
    main_module_topic_registry = MainModuleTopicRegistry()
    main_module_registry = MainModuleRegistry()

    cmk.gui.orbvis.register(
        permission_section_registry,
        permission_registry,
        page_registry,
        main_module_topic_registry,
        main_module_registry,
    )

    assert "orbvis" in permission_section_registry
    assert "orbvis.use" in permission_registry
    assert "orbvis.configure" in permission_registry
    assert "orbvis" in page_registry
    # MainModuleTopicRegistry keys on the topic name, MainModuleRegistry on the
    # module's mode_or_url (cmk/gui/watolib/main_menu.py).
    assert "maps" in main_module_topic_registry
    assert "orbvis.py#/admin" in main_module_registry
