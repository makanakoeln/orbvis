# OrbVis main navigation menu entry – compatible with Checkmk 2.3, 2.4 and 2.5
# Installed via MKP to: local/share/check_mk/web/plugins/wato/orbvis_menu.py

import os

from cmk.gui.i18n import _

_SITE = os.environ.get("OMD_SITE", "")

try:
    from cmk.gui.logged_in import user as _cmk_user
    _HAS_CMK_USER = True
except ImportError:
    try:
        from cmk.gui.globals import user as _cmk_user  # type: ignore[no-redef]
        _HAS_CMK_USER = True
    except ImportError:
        _HAS_CMK_USER = False


def _user_may_use() -> bool:
    if not _HAS_CMK_USER:
        return True
    try:
        return _cmk_user.may("orbvis.use")
    except Exception:
        return True


# (name, title, url-suffix, sort_index, icon)
_ITEMS = [
    ("orbvis_boards",      "Boards",      "",                    10, "save_dashboard"),
    ("orbvis_settings",    "Settings",    "#/admin/settings",    20, "configuration"),
    ("orbvis_connections", "Connections", "#/admin/connections", 30, "sites"),
    ("orbvis_icons",       "Icons",       "#/admin/icons",       40, "icons"),
]


try:
    # CMK 2.5+
    from cmk.gui.main_menu import main_menu_registry
    from cmk.gui.main_menu_types import MainMenu, MainMenuItem, MainMenuTopic

    def _orbvis_topics_25(_user_permissions: object) -> list:
        if not _user_may_use():
            return []
        return [
            MainMenuTopic(
                name="orbvis",
                title=_("OrbVis"),
                icon="save_dashboard",
                entries=[
                    MainMenuItem(
                        name=name,
                        title=_(title),
                        url=f"/{_SITE}/orbvis/{suffix}",
                        sort_index=idx,
                        icon=icon,
                    )
                    for name, title, suffix, idx, icon in _ITEMS
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
            search=None,
        )
    )

except ImportError:
    try:
        # CMK 2.3 / 2.4
        from cmk.gui.main_menu import mega_menu_registry
        from cmk.gui.type_defs import MegaMenu, TopicMenuItem, TopicMenuTopic

        def _orbvis_topics_24() -> list:
            if not _user_may_use():
                return []
            return [
                TopicMenuTopic(
                    name="orbvis",
                    title=_("OrbVis"),
                    icon="save_dashboard",
                    items=[
                        TopicMenuItem(
                            name=name,
                            title=_(title),
                            url=f"/{_SITE}/orbvis/{suffix}",
                            sort_index=idx,
                            icon=icon,
                        )
                        for name, title, suffix, idx, icon in _ITEMS
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
        pass
