# OrbVis – main navigation bar entry (after Setup)
# Supports Checkmk 2.4, 2.5, and 2.6+

import os

_SITE = os.environ.get("OMD_SITE", "")

try:
    # Checkmk 2.4
    from cmk.gui.i18n import _
    from cmk.gui.main_menu import mega_menu_registry
    from cmk.gui.type_defs import MegaMenu, TopicMenuItem, TopicMenuTopic

    def _orbvis_topics_24() -> list:
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
                        name="orbvis_images",
                        title=_("Images"),
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
            topics=_orbvis_topics_24,
        )
    )

except ImportError:
    try:
        # Checkmk 2.5
        from cmk.gui.i18n import _
        from cmk.gui.main_menu import main_menu_registry
        from cmk.gui.main_menu_types import MainMenu, MainMenuItem, MainMenuTopic
        from cmk.gui.utils.roles import UserPermissions

        def _orbvis_topics_25(user_permissions: UserPermissions) -> list:
            return [
                MainMenuTopic(
                    name="orbvis",
                    title=_("OrbVis"),
                    icon="save_dashboard",
                    entries=[
                        MainMenuItem(
                            name="orbvis_boards",
                            title=_("Boards"),
                            url=f"/{_SITE}/orbvis/",
                            sort_index=10,
                            icon="save_dashboard",
                        ),
                        MainMenuItem(
                            name="orbvis_settings",
                            title=_("Settings"),
                            url=f"/{_SITE}/orbvis/#/admin/settings",
                            sort_index=20,
                            icon="configuration",
                        ),
                        MainMenuItem(
                            name="orbvis_connections",
                            title=_("Connections"),
                            url=f"/{_SITE}/orbvis/#/admin/connections",
                            sort_index=30,
                            icon="sites",
                        ),
                        MainMenuItem(
                            name="orbvis_images",
                            title=_("Images"),
                            url=f"/{_SITE}/orbvis/#/admin/icons",
                            sort_index=40,
                            icon="icons",
                        ),
                    ],
                )
            ]

        main_menu_registry.register(
            MainMenu(
                name="orbvis",
                title=_("OrbVis"),
                icon="save_dashboard",
                sort_index=16,
                topics=_orbvis_topics_25,
            )
        )

    except ImportError:
        pass  # Checkmk 2.6+ uses a different plugin mechanism; sidebar snapin still works
