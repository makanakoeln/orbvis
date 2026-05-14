# OrbVis permission declarations for Checkmk 2.4+
# Installed via MKP to: local/lib/check_mk/gui/plugins/wato/orbvis_permissions.py

import json
import os
import pathlib

try:
    from cmk.gui.i18n import _, _l
    from cmk.gui.permissions import (
        declare_dynamic_permissions,
        declare_permission,
        declare_permission_section,
        permission_registry,
    )

    _BOARDS_DIR = pathlib.Path(os.environ.get("OMD_ROOT", "")) / "var" / "orbvis" / "boards"

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
        _l(
            "Grants write access to all OrbVis boards. Allows creating, modifying and deleting boards."
        ),
        ["admin"],
    )
    declare_permission(
        "orbvis.configure",
        _l("Configure OrbVis"),
        _l(
            "Grants access to OrbVis general settings, connections and images. "
            "Shows the corresponding entries in the OrbVis main menu."
        ),
        ["admin"],
    )

    _declared_board_perms: set[str] = set()

    def _declare_board_permissions() -> None:
        """Declare per-board view/edit permissions dynamically at load time."""
        # Unregister only previously declared per-board permissions so deleted
        # boards disappear from the WATO roles UI without an Apache restart.
        for key in _declared_board_perms:
            permission_registry.unregister(key)
        _declared_board_perms.clear()

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
            _declared_board_perms.add(f"orbvis.view_{name}")
            _declared_board_perms.add(f"orbvis.edit_{name}")

    declare_dynamic_permissions(_declare_board_permissions)

except Exception:
    pass
