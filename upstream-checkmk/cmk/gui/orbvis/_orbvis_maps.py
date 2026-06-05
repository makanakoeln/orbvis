#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import cmk.utils.paths
from cmk.gui.config import Config
from cmk.gui.htmllib.html import html
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.sidebar import footnotelinks, SidebarSnapin

from ._boards import BoardSummary, load_board_summaries
from ._orbvis_auth import declare_board_permissions

_BASE_URL = "../orbvis/#/boards"
_EDIT_URL = "../orbvis/"


def _is_local_install() -> bool:
    """Whether the OrbVis backend is set up on this site

    The board files may have been pushed here by the configuration sync from a
    central site that runs OrbVis — in that case there is no local backend to
    link to. The Apache reverse proxy drop-in is written by `orbvis-setup` and
    sits outside the synchronized paths, so its presence indicates a working
    local setup.
    """
    return (cmk.utils.paths.omd_root / "etc" / "apache" / "conf.d" / "orbvis.conf").is_file()


def _user_may_view_board(name: str) -> bool:
    return user.may("orbvis.use") and (
        user.may("orbvis.view_all") or user.may(f"orbvis.view_{name}")
    )


class OrbVisBoards(SidebarSnapin):
    @staticmethod
    def type_name() -> str:
        return "orbvis_boards"

    @classmethod
    def title(cls) -> str:
        return _("OrbVis boards")

    @classmethod
    def description(cls) -> str:
        return _("List of available OrbVis boards")

    @classmethod
    def refresh_regularly(cls) -> bool:
        return False

    def show(self, config: Config) -> None:
        if not _is_local_install():
            html.p(_("OrbVis is not set up on this site."))
            return

        # The per-board permissions are dynamic and may not have been declared
        # in this request yet, but user.may() can only grant declared ones.
        declare_board_permissions()

        boards = [board for board in load_board_summaries() if _user_may_view_board(board.name)]
        if boards:
            self._show_board_list(boards)
        else:
            html.p(_("No OrbVis boards found."))

        footnotelinks([(_("Open OrbVis"), _EDIT_URL)])

    def _show_board_list(self, boards: Sequence[BoardSummary]) -> None:
        html.open_ul()
        for board in boards:
            html.open_li()
            html.a(board.alias, href=f"{_BASE_URL}/{board.name}", target="main", class_="link")
            html.close_li()
        html.close_ul()
