# OrbVis sidebar snapin – compatible with Checkmk 2.3 and 2.4
# Installed via MKP to: local/share/check_mk/web/plugins/sidebar/orbvis_sidebar.py

import json
import os
import pathlib
from typing import List, Tuple

from cmk.gui.htmllib.html import html
from cmk.gui.i18n import _

# Import compatibility: 2.4 vs 2.3
try:
    from cmk.gui.sidebar._snapin import SidebarSnapin, snapin_registry  # CMK 2.4
    try:
        from cmk.gui.sidebar._snapin._helpers import footnotelinks
    except ImportError:
        from cmk.gui.sidebar._snapin import footnotelinks  # type: ignore[no-redef]
except ImportError:
    from cmk.gui.plugins.sidebar.utils import SidebarSnapin, snapin_registry  # type: ignore[no-redef] # CMK 2.3
    from cmk.gui.plugins.sidebar.utils import footnotelinks  # type: ignore[no-redef]

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


_BOARDS_DIR = pathlib.Path(os.environ.get("OMD_ROOT", "")) / "local" / "share" / "orbvis" / "boards"
_SITE = os.environ.get("OMD_SITE", "")
_BASE_URL = f"/{_SITE}/orbvis/#/boards"
_EDIT_URL = f"/{_SITE}/orbvis/#/"


def _get_boards() -> List[Tuple[str, str]]:
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

    def show(self) -> None:
        boards = [(n, a) for n, a in _get_boards() if _user_may_view_board(n)]
        if not boards:
            html.p(_("No OrbVis boards found."))
        else:
            html.open_ul(class_="snapin_nagtree")
            for name, alias in boards:
                url = f"{_BASE_URL}/{name}"
                html.open_li()
                html.open_a(href=url, target="main", title=alias)
                html.icon("network_topology", title=None)
                html.write_text(f" {alias}")
                html.close_a()
                html.close_li()
            html.close_ul()

        footnotelinks([(_("Open OrbVis"), _EDIT_URL)])
