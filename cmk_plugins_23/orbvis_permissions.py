# OrbVis permission declarations for Checkmk 2.3
# Installed via MKP to: local/share/check_mk/web/plugins/wato/orbvis_permissions.py

import json
import os
import pathlib

try:
    from cmk.gui.i18n import _, _l
    from cmk.gui.permissions import (
        declare_dynamic_permissions,
        declare_permission,
        declare_permission_section,
    )

    _BOARDS_DIR = (
        pathlib.Path(os.environ.get("OMD_ROOT", "")) / "local" / "share" / "orbvis" / "boards"
    )

    declare_permission_section("orbvis", _("OrbVis"), prio=75)

    declare_permission(
        "orbvis.use",
        _l("Use OrbVis"),
        _l("Allows the user to access OrbVis at all."),
        ["admin", "user"],
    )
    declare_permission(
        "orbvis.view_all",
        _l("View all boards"),
        _l("Grants read access to all OrbVis boards."),
        ["admin", "user"],
    )
    declare_permission(
        "orbvis.edit_all",
        _l("Edit all boards"),
        _l("Grants write access to all OrbVis boards. Allows creating, modifying and deleting boards."),
        ["admin"],
    )

    def _declare_board_permissions() -> None:
        """Declare per-board view/edit permissions dynamically at load time."""
        if not _BOARDS_DIR.is_dir():
            return
        for p in sorted(_BOARDS_DIR.glob("*.json")):
            if p.stem.startswith("demo-") or p.stem == "demo":
                continue
            try:
                data = json.loads(p.read_text())
                name = data.get("name") or p.stem
                alias = data.get("alias") or name
            except Exception:
                name = p.stem
                alias = p.stem
            declare_permission(
                f"orbvis.view_{name}",
                f"OrbVis: View board '{alias}'",
                f"Grants read access to the OrbVis board '{alias}'.",
                ["admin", "user"],
            )
            declare_permission(
                f"orbvis.edit_{name}",
                f"OrbVis: Edit board '{alias}'",
                f"Grants write access to the OrbVis board '{alias}'.",
                ["admin"],
            )

    declare_dynamic_permissions(_declare_board_permissions)

except Exception:
    pass
