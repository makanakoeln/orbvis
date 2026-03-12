# OrbVis – main navigation bar entry (after Setup)

import os

from cmk.gui.i18n import _
from cmk.gui.main_menu import mega_menu_registry
from cmk.gui.type_defs import MegaMenu, TopicMenuItem, TopicMenuTopic

_SITE = os.environ.get("OMD_SITE", "")


def _orbvis_topics() -> list[TopicMenuTopic]:
    return [
        TopicMenuTopic(
            name="orbvis",
            title=_("OrbVis"),
            icon="save_dashboard",
            items=[
                TopicMenuItem(
                    name="orbvis_boards",
                    title=_("Boards"),
                    url=f"/{_SITE}/orbvis/",
                    sort_index=10,
                    icon="save_dashboard",
                ),
                TopicMenuItem(
                    name="orbvis_settings",
                    title=_("Settings"),
                    url=f"/{_SITE}/orbvis/#/admin/settings",
                    sort_index=20,
                    icon="configuration",
                ),
                TopicMenuItem(
                    name="orbvis_connections",
                    title=_("Connections"),
                    url=f"/{_SITE}/orbvis/#/admin/connections",
                    sort_index=30,
                    icon="sites",
                ),
                TopicMenuItem(
                    name="orbvis_icons",
                    title=_("Icons"),
                    url=f"/{_SITE}/orbvis/#/admin/icons",
                    sort_index=40,
                    icon="icons",
                ),
            ],
        )
    ]


mega_menu_registry.register(
    MegaMenu(
        name="orbvis",
        title=_("OrbVis"),
        icon="save_dashboard",
        sort_index=16,
        topics=_orbvis_topics,
    )
)
