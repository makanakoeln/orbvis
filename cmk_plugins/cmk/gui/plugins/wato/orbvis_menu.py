# OrbVis – main navigation bar entry (after Setup)
# Supports Checkmk 2.4, 2.5, and 2.6+

import os

_SITE = os.environ.get("OMD_SITE", "")


class _SelfActive(str):
    """str subclass where appending '_active' returns the icon itself.

    CMK constructs the nav-bar active-state icon as ``popup_trigger.icon + "_active"``.
    Using this class as the icon name makes that expression return the original icon
    instead of a non-existing ``*_active`` variant, avoiding the placeholder fallback.
    """

    def __add__(self, other: object) -> "_SelfActive":
        if other == "_active":
            return self
        return type(self)(str.__add__(self, str(other)))


try:
    from cmk.gui.globals import user as _cmk_user
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
    # Checkmk 2.4
    from cmk.gui.i18n import _
    from cmk.gui.main_menu import mega_menu_registry
    from cmk.gui.sidebar.main_menu import MainMenuRenderer as _Renderer24
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

    _orig_get_items_24 = _Renderer24._get_main_menu_items

    def _patched_get_items_24(self):  # type: ignore[no-untyped-def]
        return [
            item._replace(icon=_SelfActive(str(item.icon))) if item.name == "orbvis" else item
            for item in _orig_get_items_24(self)
        ]

    _Renderer24._get_main_menu_items = _patched_get_items_24  # type: ignore[method-assign]

except ImportError:
    try:
        # Checkmk 2.5
        from cmk.gui.i18n import _
        from cmk.gui.main_menu import main_menu_registry
        from cmk.gui.main_menu_types import MainMenu, MainMenuItem, MainMenuTopic
        from cmk.gui.sidebar.main_menu import MainMenuRenderer as _Renderer25
        from cmk.gui.type_defs import IconNames, StaticIcon
        from cmk.gui.utils.roles import UserPermissions

        def _orbvis_topics_25(user_permissions: UserPermissions) -> list:
            if not _user_may_use():
                return []
            return [
                MainMenuTopic(
                    name="orbvis",
                    title=_("OrbVis"),
                    icon=StaticIcon(IconNames.save_dashboard),
                    entries=[
                        MainMenuItem(
                            name="orbvis_boards",
                            title=_("Boards"),
                            url=f"/{_SITE}/orbvis/",
                            sort_index=10,
                            icon=StaticIcon(IconNames.save_dashboard),
                        ),
                        MainMenuItem(
                            name="orbvis_settings",
                            title=_("Settings"),
                            url=f"/{_SITE}/orbvis/#/admin/settings",
                            sort_index=20,
                            icon=StaticIcon(IconNames.configuration),
                        ),
                        MainMenuItem(
                            name="orbvis_connections",
                            title=_("Connections"),
                            url=f"/{_SITE}/orbvis/#/admin/connections",
                            sort_index=30,
                            icon=StaticIcon(IconNames.sites),
                        ),
                        MainMenuItem(
                            name="orbvis_images",
                            title=_("Images"),
                            url=f"/{_SITE}/orbvis/#/admin/icons",
                            sort_index=40,
                            icon=StaticIcon(IconNames.icons),
                        ),
                    ],
                )
            ]

        main_menu_registry.register(
            MainMenu(
                name="orbvis",
                title=_("OrbVis"),
                icon=StaticIcon(IconNames.save_dashboard),
                sort_index=16,
                topics=_orbvis_topics_25,
            )
        )

        _orig_show_25 = _Renderer25._show_main_menu_content

        def _patched_show_25(self, user_permissions: UserPermissions, popup_triggers: list) -> None:  # type: ignore[no-untyped-def]
            patched = [
                pt._replace(icon=_SelfActive(str(pt.icon))) if pt.name == "orbvis" else pt
                for pt in popup_triggers
            ]
            _orig_show_25(self, user_permissions, patched)

        _Renderer25._show_main_menu_content = _patched_show_25  # type: ignore[method-assign]

    except ImportError:
        try:
            # Checkmk 2.6+
            from cmk.gui.i18n import _
            from cmk.gui.main_menu import main_menu_registry
            from cmk.gui.main_menu_types import MainMenuItem
            from cmk.gui.utils.roles import UserPermissions
            from cmk.shared_typing.main_menu import NavItemIdEnum, NavItemShortcut, NavItemTopic, NavItemTopicEntry

            # NavItemIdEnum is a closed str-Enum; extend it at runtime so that
            # NavItemIdEnum("orbvis") succeeds inside _get_nav_item_from_main_menu_item.
            _id = "orbvis"
            _member = str.__new__(NavItemIdEnum, _id)
            _member._name_ = _id  # type: ignore[attr-defined]
            _member._value_ = _id  # type: ignore[attr-defined]
            NavItemIdEnum._value2member_map_[_id] = _member  # type: ignore[attr-defined]
            NavItemIdEnum._member_map_[_id] = _member  # type: ignore[attr-defined]
            NavItemIdEnum._member_names_.append(_id)  # type: ignore[attr-defined]
            type.__setattr__(NavItemIdEnum, _id, _member)

            def _orbvis_topics_26(user_permissions: UserPermissions) -> list:
                if not _user_may_use():
                    return []
                return [
                    NavItemTopic(
                        id="orbvis",
                        title=_("OrbVis"),
                        sort_index=10,
                        entries=[
                            NavItemTopicEntry(
                                id="orbvis_boards",
                                title=_("Boards"),
                                url=f"/{_SITE}/orbvis/",
                                target="main",
                                sort_index=10,
                            ),
                            NavItemTopicEntry(
                                id="orbvis_settings",
                                title=_("Settings"),
                                url=f"/{_SITE}/orbvis/#/admin/settings",
                                target="main",
                                sort_index=20,
                            ),
                            NavItemTopicEntry(
                                id="orbvis_connections",
                                title=_("Connections"),
                                url=f"/{_SITE}/orbvis/#/admin/connections",
                                target="main",
                                sort_index=30,
                            ),
                            NavItemTopicEntry(
                                id="orbvis_images",
                                title=_("Images"),
                                url=f"/{_SITE}/orbvis/#/admin/icons",
                                target="main",
                                sort_index=40,
                            ),
                        ],
                    )
                ]

            main_menu_registry.register(
                MainMenuItem(
                    id=NavItemIdEnum(_id),
                    title=_("OrbVis"),
                    sort_index=16,
                    shortcut=NavItemShortcut(key="o", alt=True),
                    get_topics=_orbvis_topics_26,
                )
            )

        except ImportError:
            pass
