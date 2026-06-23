#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Contribute a "Maps" topic to the Monitor mega-menu.

Checkmk has no plugin hook to add a topic to the existing Monitor menu, so at
registration time the ``view_menu_topics`` callback is composed: the default
topics plus the ones returned here (see this package's register() and MERGE.md).
"""

from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.type_defs import IconNames
from cmk.gui.utils.roles import UserPermissions
from cmk.shared_typing.main_menu import DefaultIcon, NavItemTopic, NavItemTopicEntry

from ._maps import load_map_summaries
from ._orbvis_auth import declare_map_permissions


def _user_may_view_map(name: str) -> bool:
    return user.may("orbvis.view_all") or user.may(f"orbvis.view_{name}")


def orbvis_monitor_topics(_user_permissions: UserPermissions) -> list[NavItemTopic]:
    if not user.may("orbvis.use"):
        return []
    # Per-map permissions are dynamic and may not have been declared in this
    # request yet, but user.may() can only grant declared ones.
    declare_map_permissions()
    entries = [
        NavItemTopicEntry(
            id=f"orbvis_map_{summary.name}",
            title=summary.alias,
            url=f"orbvis.py#/maps/{summary.name}",
            target="main",
            sort_index=10 + index,
            icon=DefaultIcon(id=IconNames.dashboard),
        )
        for index, summary in enumerate(load_map_summaries())
        if _user_may_view_map(summary.name)
    ]
    if not entries:
        return []
    return [
        NavItemTopic(
            id="orbvis_maps",
            title=_("Maps"),
            icon=DefaultIcon(id=IconNames.topic_visualization),
            entries=entries,
            sort_index=15,
        )
    ]
