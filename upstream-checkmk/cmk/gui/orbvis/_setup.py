#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Register the Checkmk Maps configuration entry in the Setup menu."""

from cmk.gui.i18n import _, _l
from cmk.gui.type_defs import DynamicIcon, DynamicIconName, IconNames, StaticIcon
from cmk.gui.watolib.main_menu import (
    ABCMainModule,
    MainModuleRegistry,
    MainModuleTopic,
    MainModuleTopicRegistry,
)

MainModuleTopicMaps = MainModuleTopic(
    name="maps",
    title=_l("Maps"),
    icon_name=DynamicIconName("topic_visualization"),
    sort_index=145,
)


class MainModuleMaps(ABCMainModule):
    @property
    def mode_or_url(self) -> str:
        # Opens the Maps SPA on its admin route (the hash is client-side).
        return "orbvis.py#/admin"

    @property
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicMaps

    @property
    def title(self) -> str:
        return _("Maps")

    @property
    def icon(self) -> StaticIcon | DynamicIcon:
        return StaticIcon(IconNames.save_dashboard)

    @property
    def permission(self) -> None | str:
        return "orbvis.configure"

    @property
    def description(self) -> str:
        return _("Configure Checkmk Maps: connections, settings and images.")

    @property
    def sort_index(self) -> int:
        return 10

    @property
    def is_show_more(self) -> bool:
        return False


def register(
    main_module_topic_registry: MainModuleTopicRegistry,
    main_module_registry: MainModuleRegistry,
) -> None:
    main_module_topic_registry.register(MainModuleTopicMaps)
    main_module_registry.register(MainModuleMaps)
