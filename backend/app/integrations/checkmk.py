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
# True when cmk.gui.userdb.store is importable (some CMK versions lack transitive deps)
_userdb_store_available = False


def setup() -> None:
    """Call once at startup (before any cmk imports elsewhere)."""
    global available, _userdb_store_available
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
        return
    try:
        from cmk.gui.userdb.store import load_user as _  # noqa: F401

        _userdb_store_available = True
    except Exception as e:
        log.debug("cmk.gui.userdb.store not available (%s) — using file fallback", e)


def get_monitoring_core() -> str | None:
    """Return 'cmc', 'nagios', or None (not in OMD or file unreadable).

    Reads CONFIG_CORE from $OMD_ROOT/etc/omd/site.conf — stable across CMK 2.3–master.
    Never raises; fails safe (returns None) so callers can show all UI fields.
    """
    if not settings.checkmk_omd_root:
        return None
    site_conf = Path(settings.checkmk_omd_root) / "etc" / "omd" / "site.conf"
    try:
        text = site_conf.read_text(encoding="utf-8")
    except OSError as exc:
        log.debug("get_monitoring_core: cannot read %s: %s", site_conf, exc)
        return None
    for line in text.splitlines():
        if line.strip().startswith("CONFIG_CORE="):
            return line.split("=", 1)[1].strip().strip("'\"")
    log.debug("get_monitoring_core: CONFIG_CORE not found in %s", site_conf)
    return None


def load_user(username: str) -> dict[str, Any]:
    """Load all available Checkmk attributes for a user.

    Tries cmk.gui.userdb.store (the proper CMK API) first:
    - load_user()        → wato user spec (language, roles, alias, …)
    - load_custom_attr() → per-user runtime attrs (ui_theme, …)

    Falls back to direct file parsing when the CMK API is unavailable.
    Returns an empty dict when the user is not found.
    """
    if not available or not settings.checkmk_omd_root:
        return {}
    if _userdb_store_available:
        try:
            from cmk.gui.userdb.store import load_custom_attr as _load_custom_attr
            from cmk.gui.userdb.store import load_user as _load_user

            data = dict(_load_user(username))
            for key in ("ui_theme",):
                val = _load_custom_attr(user_id=username, key=key, parser=lambda x: x)
                if val is not None:
                    data[key] = val
            return data
        except Exception as e:
            log.debug(
                "load_user(%s) via cmk.gui.userdb.store failed (%s) — using fallback", username, e
            )
    return _load_user_fallback(username)


def _load_user_fallback(username: str) -> dict[str, Any]:
    """Direct file fallback when cmk.gui.userdb.store is unavailable."""
    try:
        omd_root = Path(settings.checkmk_omd_root)

        # Static user config (roles, alias, email, language, …) via exec()
        users_mk = omd_root / "etc" / "check_mk" / "multisite.d" / "wato" / "users.mk"
        ns: dict = {"multisite_users": {}}
        if users_mk.is_file():
            exec(compile(users_mk.read_bytes(), str(users_mk), "exec"), ns)  # nosec B102 — Checkmk .mk files use Python syntax; no safe alternative to exec()
        user_data: dict = dict(ns["multisite_users"].get(username, {}))

        # Per-user runtime attrs override wato data (plain-text .mk files)
        profile_dir = omd_root / "var" / "check_mk" / "web" / username
        if profile_dir.is_dir():
            for attr_file in profile_dir.glob("*.mk"):
                key = attr_file.stem
                val = attr_file.read_text().strip()
                if val:
                    user_data[key] = val

        return user_data
    except Exception as e:
        log.warning("_load_user_fallback(%s): %s", username, e)
        return {}
