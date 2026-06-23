#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.pages import PageRegistry
from cmk.gui.permissions import PermissionRegistry, PermissionSectionRegistry
from cmk.gui.watolib.main_menu import MainModuleRegistry, MainModuleTopicRegistry

from . import _orbvis_auth, _pages, _setup
from ._monitor_menu import orbvis_monitor_topics

# Re-exported so community_registration can compose it into the Monitor menu's
# view_menu_topics callback (Checkmk has no plugin hook to add a topic to the
# existing Monitor mega-menu). See MERGE.md.
__all__ = ["orbvis_monitor_topics", "register"]


def register(
    permission_section_registry: PermissionSectionRegistry,
    permission_registry: PermissionRegistry,
    page_registry: PageRegistry,
    main_module_topic_registry: MainModuleTopicRegistry,
    main_module_registry: MainModuleRegistry,
) -> None:
    _orbvis_auth.register(permission_section_registry, permission_registry)
    _pages.register(page_registry)
    _setup.register(main_module_topic_registry, main_module_registry)
