"""
Optional Checkmk Python integration.

Adds $OMD_ROOT/lib/python3 to sys.path when running inside an OMD site,
making cmk.* modules importable. Falls back gracefully when standalone.
"""
import logging
import sys
from pathlib import Path
from typing import Any

from app.core.config import settings

log = logging.getLogger(__name__)

# True after setup() succeeded and cmk.* modules are importable
available = False


def setup() -> None:
    """Call once at startup (before any cmk imports elsewhere)."""
    global available
    if not settings.checkmk_omd_root:
        return
    lib_path = str(Path(settings.checkmk_omd_root) / "lib" / "python3")
    if lib_path not in sys.path:
        sys.path.insert(0, lib_path)
    try:
        import cmk.utils.paths  # noqa: F401 — smoke test
        available = True
        log.info("Checkmk Python modules available (%s)", lib_path)
    except ImportError as e:
        log.warning("Checkmk Python modules not importable: %s", e)


def load_user(username: str) -> dict[str, Any]:
    """Load all available Checkmk attributes for a user.

    Reads from two sources (no Flask context required):
    - etc/check_mk/multisite.d/wato/users.mk  → roles, email, alias, …
    - var/check_mk/web/{username}/*.mk         → runtime attrs (ui_theme, …)

    Uses settings.checkmk_omd_root for path resolution (guaranteed correct)
    rather than cmk.utils.paths (depends on OMD_ROOT env var at import time).

    Returns an empty dict when the user is not found or cmk modules are
    unavailable.
    """
    if not available or not settings.checkmk_omd_root:
        return {}
    try:
        omd_root = Path(settings.checkmk_omd_root)

        # --- static user config (roles, alias, email, …) ---
        users_mk = omd_root / "etc" / "check_mk" / "multisite.d" / "wato" / "users.mk"
        ns: dict = {"multisite_users": {}}
        if users_mk.is_file():
            exec(compile(users_mk.read_bytes(), str(users_mk), "exec"), ns)  # noqa: S102
        user_data: dict = dict(ns["multisite_users"].get(username, {}))

        # --- per-user runtime attributes (plain-text .mk files) ---
        profile_dir = omd_root / "var" / "check_mk" / "web" / username
        if profile_dir.is_dir():
            for attr_file in profile_dir.glob("*.mk"):
                key = attr_file.stem
                if key not in user_data:
                    val = attr_file.read_text().strip()
                    if val:
                        user_data[key] = val

        return user_data
    except Exception as e:
        log.warning("load_user(%s): %s", username, e)
        return {}
