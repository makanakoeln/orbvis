# OrbVis sidebar snapin – shows all available OrbVis boards as links

import json
import os
import pathlib

from cmk.gui.htmllib.html import html
from cmk.gui.i18n import _
from cmk.gui.sidebar._snapin import SidebarSnapin, snapin_registry
from cmk.gui.sidebar._snapin._helpers import footnotelinks

try:
    from cmk.gui.logged_in import user as _cmk_user

    _HAS_CMK_USER = True
except ImportError:
    try:
        from cmk.gui.globals import user as _cmk_user  # type: ignore[no-redef]

        _HAS_CMK_USER = True
    except ImportError:
        _HAS_CMK_USER = False


def _user_may_view_board(name: str) -> bool:
    """Return True if the current Checkmk user may view this board."""
    if not _HAS_CMK_USER:
        return True
    try:
        return _cmk_user.may("orbvis.use") and (
            _cmk_user.may("orbvis.view_all") or _cmk_user.may(f"orbvis.view_{name}")
        )
    except Exception:
        return True


_OMD_ROOT = pathlib.Path(os.environ.get("OMD_ROOT", ""))
_BOARDS_DIR = _OMD_ROOT / "var" / "orbvis" / "boards"
_LOCAL_INSTALL_MARKER = _OMD_ROOT / "etc" / "apache" / "conf.d" / "orbvis.conf"
_SITE = os.environ.get("OMD_SITE", "")
_BASE_URL = f"/{_SITE}/orbvis/#/boards"
_EDIT_URL = f"/{_SITE}/orbvis/#/"


def _is_local_install() -> bool:
    """Whether OrbVis is installed on this OMD site.

    The plugin file itself may have been pushed here by the WATO replication
    snapshot from a central site that runs OrbVis — in that case there's no
    local backend to link to, so rendering a "Boards" sidebar would 404 on
    every click. Use the Apache vhost drop-in (etc/apache/conf.d/orbvis.conf)
    as the install marker since it sits outside the replication paths and is
    only written by install_cmk.sh / orbvis-setup.
    """
    return _LOCAL_INSTALL_MARKER.is_file()


def _get_maps() -> list[tuple[str, str]]:
    results = []
    if not _BOARDS_DIR.is_dir():
        return results
    for p in sorted(_BOARDS_DIR.glob("*.json")):
        if p.stem.startswith("demo-") or p.stem == "demo":
            continue
        try:
            data = json.loads(p.read_text())
            name = data.get("name") or p.stem
            alias = data.get("alias") or name
            results.append((name, alias))
        except Exception:
            results.append((p.stem, p.stem))
    return results


@snapin_registry.register
class OrbVisBoardsSnapin(SidebarSnapin):
    @staticmethod
    def type_name() -> str:
        return "orbvis_boards"

    @classmethod
    def title(cls) -> str:
        return _("OrbVis Boards")

    @classmethod
    def description(cls) -> str:
        return _("Links to OrbVis monitoring boards")

    @classmethod
    def allowed_roles(cls):
        return ["admin", "user", "guest"]

    def show(self, _config=None) -> None:
        if not _is_local_install():
            html.p(_("OrbVis is not installed on this site."))
            return
        maps = [(n, a) for n, a in _get_maps() if _user_may_view_board(n)]
        if not maps:
            html.p(_("No OrbVis boards found."))
        else:
            html.open_ul(class_="snapin_nagtree")
            for name, alias in maps:
                url = f"{_BASE_URL}/{name}"
                html.open_li()
                html.open_a(href=url, target="main", title=alias)
                html.icon("network_topology", title=None)
                html.write_text(f" {alias}")
                html.close_a()
                html.close_li()
            html.close_ul()

        footnotelinks([(_("Edit"), _EDIT_URL)])
