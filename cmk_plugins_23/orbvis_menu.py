# OrbVis main navigation menu entry – compatible with Checkmk 2.3 and 2.4
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


try:
    # CMK 2.3 / 2.4
    from cmk.gui.main_menu import mega_menu_registry
    from cmk.gui.type_defs import MegaMenu, TopicMenuItem, TopicMenuTopic

    def _orbvis_topics() -> list:
        if not _user_may_use():
            return []
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

except Exception:
    # Graceful degradation if menu API unavailable
    pass
