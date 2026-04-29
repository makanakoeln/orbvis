"""
Optional Checkmk Python integration.

Adds $OMD_ROOT/lib/python3 to sys.path when running inside an OMD site,
making cmk.* modules importable. Falls back gracefully when standalone.
"""

import logging
import sys
import threading
import time as _time
from collections.abc import Iterable
from pathlib import Path

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
    omd_lib = Path(settings.checkmk_omd_root) / "lib"

    # Add lib/python3 (traditional cmk.gui, cmk.base, …)
    lib_path = str(omd_lib / "python3")
    if lib_path not in sys.path:
        sys.path.insert(0, lib_path)

    # Add lib/pythonX.Y/site-packages (cmk.trace, cmk.livestatus_client, … since CMK 2.4)
    for candidate in sorted(omd_lib.glob("python3.*/site-packages"), reverse=True):
        p = str(candidate)
        if p not in sys.path:
            sys.path.insert(0, p)

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


def load_user(username: str) -> dict[str, object]:
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


# ---------------------------------------------------------------------------
# Permission checking via Checkmk roles
# ---------------------------------------------------------------------------

# Default roles that have each OrbVis permission (mirrors cmk_plugins declarations).
_ORBVIS_PERM_DEFAULTS: dict[str, frozenset[str]] = {
    "orbvis.use": frozenset({"admin", "user"}),
    "orbvis.view_all": frozenset({"admin", "user"}),
    "orbvis.edit_all": frozenset({"admin"}),
}
_ORBVIS_VIEW_DEFAULTS: frozenset[str] = frozenset({"admin", "user"})
_ORBVIS_EDIT_DEFAULTS: frozenset[str] = frozenset({"admin"})

# Built-in CMK permission defaults not stored in roles.mk (only deviations are stored there).
# Source: cmk/gui/default_permissions.py — keep in sync when adding new checks.
_CMK_PERM_DEFAULTS: dict[str, frozenset[str]] = {
    "general.see_all": frozenset({"admin", "guest"}),
}


def _orbvis_perm_defaults(perm_name: str) -> frozenset[str]:
    if perm_name in _CMK_PERM_DEFAULTS:
        return _CMK_PERM_DEFAULTS[perm_name]
    if perm_name in _ORBVIS_PERM_DEFAULTS:
        return _ORBVIS_PERM_DEFAULTS[perm_name]
    if perm_name.startswith("orbvis.edit_"):
        return _ORBVIS_EDIT_DEFAULTS
    if perm_name.startswith("orbvis.view_"):
        return _ORBVIS_VIEW_DEFAULTS
    return frozenset()


_roles_cache: dict[str, object] = {}
_roles_cache_mtime: float = -1.0


def _load_roles() -> dict[str, object]:
    """Load Checkmk role configuration from roles.mk (mtime-cached).

    Returns the ``roles`` dict mapping role-id → role-spec.
    Returns an empty dict on error or when OMD_ROOT is not set.
    """
    global _roles_cache, _roles_cache_mtime
    if not settings.checkmk_omd_root:
        return {}
    roles_mk = (
        Path(settings.checkmk_omd_root) / "etc" / "check_mk" / "multisite.d" / "wato" / "roles.mk"
    )
    try:
        mtime = roles_mk.stat().st_mtime if roles_mk.is_file() else 0.0
        if mtime == _roles_cache_mtime:
            return _roles_cache
        ns: dict[str, object] = {"roles": {}}
        if roles_mk.is_file():
            exec(compile(roles_mk.read_bytes(), str(roles_mk), "exec"), ns)  # nosec B102 — Checkmk .mk files use Python syntax; no safe alternative to exec()
        roles_val = ns.get("roles", {})
        _roles_cache = roles_val if isinstance(roles_val, dict) else {}
        _roles_cache_mtime = mtime
        return _roles_cache
    except Exception as exc:
        log.warning("_load_roles: %s", exc)
        return {}


def _has_permission(
    user_data: dict[str, object], role_config: dict[str, object], perm_name: str
) -> bool:
    """Return True if the user (described by *user_data*) has *perm_name*."""
    roles_raw = user_data.get("roles", ["user"])
    roles: list[str] = (
        [r for r in roles_raw if isinstance(r, str)] if isinstance(roles_raw, list) else ["user"]
    )
    defaults = _orbvis_perm_defaults(perm_name)
    for role_id in roles:
        role_raw = role_config.get(role_id, {})
        if not isinstance(role_raw, dict):
            continue
        permissions = role_raw.get("permissions", {})
        explicit = permissions.get(perm_name) if isinstance(permissions, dict) else None
        if explicit is True:
            return True
        if explicit is False:
            continue
        # Not explicitly set → fall back to permission defaults for the base role.
        base_role = role_raw.get("basedon", role_id)
        if base_role in defaults:
            return True
    return False


def check_checkmk_permission(username: str, perm_name: str) -> bool:
    """Return True if the Checkmk user *username* has *perm_name*.

    Returns False when CHECKMK_OMD_ROOT is not configured.
    """
    if not settings.checkmk_omd_root:
        return False
    user_data = load_user(username) if available else _load_user_fallback(username)
    return _has_permission(user_data, _load_roles(), perm_name)


def check_board_permission(username: str, board_name: str, action: str) -> bool:
    """Return True if the Checkmk user may view or edit an OrbVis board.

    *action* must be ``'view'`` or ``'edit'``.
    Always returns False when CHECKMK_OMD_ROOT is not configured.
    """
    if not settings.checkmk_omd_root:
        return False
    user_data = load_user(username) if available else _load_user_fallback(username)
    role_config = _load_roles()
    if not _has_permission(user_data, role_config, "orbvis.use"):
        return False
    if action == "view":
        return _has_permission(user_data, role_config, "orbvis.view_all") or _has_permission(
            user_data, role_config, f"orbvis.view_{board_name}"
        )
    if action == "edit":
        return _has_permission(user_data, role_config, "orbvis.edit_all") or _has_permission(
            user_data, role_config, f"orbvis.edit_{board_name}"
        )
    return False


def get_user_contact_groups(username: str) -> list[str]:
    """Return the contact groups a Checkmk user belongs to.

    Returns an empty list when CHECKMK_OMD_ROOT is not configured or the user
    has no contact groups assigned.
    """
    if not settings.checkmk_omd_root:
        return []
    user_data = load_user(username) if available else _load_user_fallback(username)
    cgs = user_data.get("contactgroups", [])
    return list(cgs) if isinstance(cgs, (list, tuple)) else []


def _load_user_fallback(username: str) -> dict[str, object]:
    """Direct file fallback when cmk.gui.userdb.store is unavailable."""
    try:
        omd_root = Path(settings.checkmk_omd_root)

        # Static user config (roles, alias, email, language, …) via exec()
        users_mk = omd_root / "etc" / "check_mk" / "multisite.d" / "wato" / "users.mk"
        ns: dict[str, object] = {"multisite_users": {}}
        if users_mk.is_file():
            exec(compile(users_mk.read_bytes(), str(users_mk), "exec"), ns)  # nosec B102 — Checkmk .mk files use Python syntax; no safe alternative to exec()
        multisite_users = ns["multisite_users"]
        raw_user = multisite_users.get(username, {}) if isinstance(multisite_users, dict) else {}
        user_data: dict[str, object] = dict(raw_user) if isinstance(raw_user, dict) else {}

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


# ---------------------------------------------------------------------------
# Checkmk BI (Business Intelligence) — direct Python integration
# ---------------------------------------------------------------------------
#
# OrbVis prefers the in-process cmk.bi.* path over the REST API:
#   - no automation user / token (defunct in CMK 2.5)
#   - automatic per-user permissions via cmk.gui.user
#   - ~10× lower latency (no HTTP roundtrip, no JSON serialisation)
#
# Standalone deployments (no OMD site) fall back to REST in livestatus.py.


def cmk_bi_available() -> bool:
    """Whether the in-process BI fast path is usable in this deployment."""
    if not available:
        return False
    try:
        from cmk.gui.bi import BIManager, get_cached_bi_packs  # noqa: F401
    except Exception:
        return False
    return True


# BIManager is expensive to build (loads + compiles all aggregations from
# bi_config.bi). It holds no per-request state — only a SitesCallback that
# closes over cmk.gui.sites, which the surrounding request context refreshes
# for us — so we cache the instance for ~10s. Config edits in CMK propagate
# after at most one TTL cycle.
_BI_MANAGER_CACHE: tuple[float, object] | None = None
_BI_MANAGER_LOCK = threading.Lock()
_BI_MANAGER_TTL = 10.0


def _cached_bi_manager() -> object:
    """Return a cached BIManager. Caller must hold an application/request context."""
    global _BI_MANAGER_CACHE
    with _BI_MANAGER_LOCK:
        now = _time.time()
        if _BI_MANAGER_CACHE is not None and now - _BI_MANAGER_CACHE[0] < _BI_MANAGER_TTL:
            return _BI_MANAGER_CACHE[1]
        # cmk.gui.bi re-exports BIManager (stable across 2.3–2.5).
        from cmk.gui.bi import BIManager

        manager = BIManager()
        _BI_MANAGER_CACHE = (now, manager)
        return manager


def cmk_bi_get_aggregations_states(
    username: str | None,
    aggregation_ids: list[str],
) -> dict[str, dict[str, object]]:
    """Compute current state for a list of BI aggregations via cmk.bi.

    Synchronous — callers wrap with asyncio.to_thread(). Returns a dict keyed by
    aggregation id; entries contain ``state`` (int), ``output`` (str),
    ``acknowledged`` (bool), ``in_downtime`` (bool). Missing aggregations are
    simply absent from the result.
    """
    if not cmk_bi_available() or not aggregation_ids:
        return {}
    try:
        # BIAggregationFilter lives in cmk.bi.computer (NOT cmk.bi.filters) across 2.3–2.5.
        from cmk.bi.computer import BIAggregationFilter
        from cmk.gui.utils.script_helpers import application_and_request_context

        with application_and_request_context():
            _set_cmk_user(username)
            bi_manager = _cached_bi_manager()
            bi_filter = BIAggregationFilter([], [], [], list(aggregation_ids), [], [])
            results = bi_manager.computer.compute_result_for_filter(bi_filter)  # type: ignore[attr-defined]
            return _bi_results_to_dict(results)
    except Exception:
        log.warning("cmk.bi compute failed for %s", aggregation_ids, exc_info=True)
        return {}


def cmk_bi_list_aggregations() -> list[dict[str, str]]:
    """Return all configured BI aggregations as [{id, title, pack_id}, ...]."""
    if not cmk_bi_available():
        return []
    try:
        # cmk.gui.bi re-exports get_cached_bi_packs across 2.3–2.5.
        # The direct cmk.bi.packs path was removed in 2.5.
        from cmk.gui.bi import get_cached_bi_packs
        from cmk.gui.utils.script_helpers import application_and_request_context

        with application_and_request_context():
            packs = get_cached_bi_packs()
            packs.load_config()
            out: list[dict[str, str]] = []
            for pack in packs.get_packs().values():
                pack_id = str(getattr(pack, "id", "") or "")
                for aggr in pack.get_aggregations().values():
                    aggr_id = str(getattr(aggr, "id", "") or "")
                    if not aggr_id:
                        continue
                    title = str(getattr(aggr, "title", "") or aggr_id)
                    out.append({"id": aggr_id, "title": title, "pack_id": pack_id})
            return out
    except Exception:
        log.warning("cmk.bi list aggregations failed", exc_info=True)
        return []


def _set_cmk_user(username: str | None) -> None:
    """Best-effort: scope the current cmk.gui request to *username*.

    On failure (CMK API drift, user not in CMK, …) we silently keep the default
    application context — BI calls then run with whatever permissions the
    application user has. Per-user RBAC is degraded but the call still succeeds.
    """
    if not username:
        return
    try:
        from cmk.gui.session import session
        from cmk.gui.userdb import LoggedInUser

        session.user = LoggedInUser(username)
    except Exception as exc:
        log.debug("cannot set per-user cmk.gui context for %s: %s", username, exc)


def _bi_results_to_dict(results: object) -> dict[str, dict[str, object]]:
    """Normalise BIComputer.compute_result_for_filter output into plain dicts.

    The cmk.bi return type is ``Iterable[tuple[BIAggregation, list[NodeResultBundle]]]``,
    typed as object here so this module can be imported without cmk.* installed.
    """
    out: dict[str, dict[str, object]] = {}
    if not isinstance(results, Iterable):
        return out
    for entry in results:
        try:
            aggr, branches = entry
        except (TypeError, ValueError):
            continue
        aggr_id = str(getattr(aggr, "id", "") or "")
        if not aggr_id or not branches:
            continue
        bundle = branches[0]
        actual = getattr(bundle, "actual_result", None)
        if actual is None:
            continue
        out[aggr_id] = {
            "state": int(getattr(actual, "state", -1)),
            "output": str(getattr(actual, "output", "") or ""),
            "acknowledged": bool(getattr(actual, "acknowledged", False)),
            "in_downtime": bool(getattr(actual, "downtime_state", 0)),
        }
    return out
