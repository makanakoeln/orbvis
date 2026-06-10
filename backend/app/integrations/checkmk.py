"""
Optional Checkmk Python integration.

Adds $OMD_ROOT/lib/python3 to sys.path when running inside an OMD site,
making cmk.* modules importable. Falls back gracefully when standalone.
"""

import logging
import sys
import threading
import time as _time
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from app.core.config import settings

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class FolderScope:
    """A user's SETUP-folder *read* visibility (distinct from monitoring host
    visibility / Livestatus AuthUser).

    Checkmk gates folder reads on ``wato.see_all_folders`` (admin-only) OR
    membership in a folder's contact groups — NOT on ``general.see_all`` (which
    a guest has). So a see-all guest sees every monitored host but must not see
    SETUP folder names outside their contact groups.

    ``see_all`` → may read every folder. Otherwise a folder is readable iff its
    effective contact groups intersect ``groups``. ``key`` is a stable hashable
    identity so subscribers/snapshots with the same folder visibility share work.
    """

    see_all: bool
    groups: frozenset[str] = frozenset()

    @property
    def key(self) -> str:
        return "*" if self.see_all else "cg:" + ",".join(sorted(self.groups))

    def permits(self, permitted_groups: Iterable[str]) -> bool:
        return self.see_all or bool(self.groups & set(permitted_groups))


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


def exec_mk_file(path: Path, defaults: dict[str, Any]) -> dict[str, Any]:
    """Exec a Checkmk ``.mk`` config file and return its variable namespace.

    Threat model: ``.mk`` files are owned by the OMD site user we run as, so
    ``exec`` introduces no additional privilege boundary. Do not loosen this
    file-ownership expectation without re-auditing all callers.
    """
    ns: dict[str, Any] = dict(defaults)
    if path.is_file():
        exec(compile(path.read_bytes(), str(path), "exec"), ns)  # nosec B102 — Checkmk .mk files use Python syntax; no safe alternative to exec()
    return ns


MonitoringCore = Literal["cmc", "nagios"]


def get_monitoring_core() -> MonitoringCore | None:
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
            value = line.split("=", 1)[1].strip().strip("'\"")
            if value in ("cmc", "nagios"):
                return value  # type: ignore[return-value]
            return None
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
    if not settings.checkmk_omd_root:
        return {}
    # The file fallback needs no cmk imports, so it also serves setups where
    # the cmk packages aren't importable (``available`` is False).
    if available and _userdb_store_available:
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
    "orbvis.configure": frozenset({"admin"}),
}
_ORBVIS_VIEW_DEFAULTS: frozenset[str] = frozenset({"admin", "user"})
_ORBVIS_EDIT_DEFAULTS: frozenset[str] = frozenset({"admin"})

# Built-in CMK permission defaults not stored in roles.mk (only deviations are stored there).
# Source: cmk/gui/default_permissions.py and cmk/gui/views/command/commands.py — keep in
# sync when adding new checks.
_CMK_PERM_DEFAULTS: dict[str, frozenset[str]] = {
    "general.see_all": frozenset({"admin", "guest"}),
    # Read access to all SETUP folders regardless of contact groups. Guests do
    # NOT have it (unlike general.see_all) — they can monitor all hosts but must
    # not see SETUP folder names outside their contact groups. (cmk/gui/wato)
    "wato.see_all_folders": frozenset({"admin"}),
    # Defaults per cmk/gui/views/command/commands.py; notifications/enablechecks
    # ship with no default role (admin-only unless explicitly granted).
    "action.acknowledge": frozenset({"user", "admin"}),
    "action.downtimes": frozenset({"user", "admin"}),
    "action.addcomment": frozenset({"user", "admin"}),
    "action.reschedule": frozenset({"user", "admin"}),
    "action.notifications": frozenset(),
    "action.enablechecks": frozenset(),
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

    See :func:`exec_mk_file` for the file-ownership threat model.
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
        roles_val = exec_mk_file(roles_mk, {"roles": {}}).get("roles", {})
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


def resolve_folder_scope(username: str, is_admin: bool) -> FolderScope:
    """The SETUP-folder read visibility for a user (see :class:`FolderScope`).

    Standalone (no CHECKMK_OMD_ROOT) has no folder ACLs → see all. Admins and
    ``wato.see_all_folders`` holders see all; everyone else is limited to their
    contact groups.
    """
    if not settings.checkmk_omd_root:
        return FolderScope(see_all=True)
    if is_admin or check_checkmk_permission(username, "wato.see_all_folders"):
        return FolderScope(see_all=True)
    return FolderScope(see_all=False, groups=frozenset(get_user_contact_groups(username)))


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


def check_configure_permission(username: str) -> bool:
    """Return True if the Checkmk user may manage connections, images and settings.

    Gated by ``orbvis.use`` plus the dedicated ``orbvis.configure`` permission.
    Always returns False when CHECKMK_OMD_ROOT is not configured.
    """
    if not settings.checkmk_omd_root:
        return False
    user_data = load_user(username) if available else _load_user_fallback(username)
    role_config = _load_roles()
    return _has_permission(user_data, role_config, "orbvis.use") and _has_permission(
        user_data, role_config, "orbvis.configure"
    )


def check_create_permission(username: str) -> bool:
    """Return True if the Checkmk user may create or delete boards.

    Mirrors the WATO declaration: ``orbvis.edit_all`` grants creating, modifying
    and deleting boards. Per-board ``orbvis.edit_<board>`` does not apply here —
    creating a board is not scoped to an existing board name.
    Always returns False when CHECKMK_OMD_ROOT is not configured.
    """
    if not settings.checkmk_omd_root:
        return False
    user_data = load_user(username) if available else _load_user_fallback(username)
    role_config = _load_roles()
    return _has_permission(user_data, role_config, "orbvis.use") and _has_permission(
        user_data, role_config, "orbvis.edit_all"
    )


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


def load_user_inline_help(username: str) -> bool:
    """Mirror of ``LoggedInUser.inline_help_as_text`` via CMK's own loader."""
    if not available:
        return False
    try:
        from cmk.ccc.user import UserId
        from cmk.gui.logged_in import load_user_file

        return bool(load_user_file("help", UserId(username), False, lock=False))
    except Exception as e:
        log.debug("load_user_inline_help(%s) via CMK API failed (%s)", username, e)
        return False


def _load_user_fallback(username: str) -> dict[str, object]:
    """Direct file fallback when cmk.gui.userdb.store is unavailable."""
    try:
        omd_root = Path(settings.checkmk_omd_root)

        users_mk = omd_root / "etc" / "check_mk" / "multisite.d" / "wato" / "users.mk"
        multisite_users = exec_mk_file(users_mk, {"multisite_users": {}})["multisite_users"]
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
# Checkmk BI (Business Intelligence) — direct cmk.bi.* integration
# ---------------------------------------------------------------------------
#
# OrbVis instantiates BICompiler/BIComputer directly and feeds them a custom
# SitesCallback that uses our own Livestatus client. We deliberately avoid
# cmk.gui.bi.bi_manager.BIManager (which would require cmk.gui.utils.
# script_helpers.application_and_request_context() — that builds a Flask app
# via make_wsgi_app() which crashes on editions not registered in
# cmk.gui.features.features_registry, including 2.5 ULTIMATE).
#
# The cmk.bi.* sub-package has no cmk.gui imports — it is pure compute over
# Livestatus data — so a direct integration works on every edition without
# Flask, WSGI, or edition-feature-registry shenanigans.
#
# Standalone deployments (no OMD site) fall back to REST in livestatus.py.

QueryCallback = Callable[..., Any]


def cmk_bi_available() -> bool:
    """Whether the in-process BI fast path is usable in this deployment."""
    if not available:
        return False
    try:
        from cmk.bi.compiler import BICompiler  # noqa: F401
        from cmk.bi.computer import BIComputer  # noqa: F401
    except Exception:
        return False
    return True


# Loading + compiling all aggregations from bi_config.bi is the expensive part,
# so the compiled dict is cached for ~10s (CMK config edits propagate after at
# most one TTL cycle). BIComputer/BIStatusFetcher are built FRESH per call:
# ``compute_result_for_filter`` REPLACES the shared fetcher's ``states`` dict,
# so a cached computer races with itself — concurrent computes (SSE tick vs
# REST states vs parallel tree fetches in asyncio.gather) wipe each other's
# status data mid-compute and branches flip to state -1 / PENDING. cmk.gui
# avoids this by building a request-scoped BIManager; we mirror that.
_BI_COMPILED_CACHE: tuple[float, dict[str, object]] | None = None
_BI_COMPUTER_LOCK = threading.Lock()
_BI_COMPUTER_TTL = 10.0


def _make_sites_callback(query_callback: QueryCallback, site_id: str) -> object:
    from cmk.bi.lib import SitesCallback
    from cmk.ccc.site import SiteId

    return SitesCallback(
        all_sites_with_id_and_online=lambda: [(SiteId(site_id), True)],
        query=query_callback,
        translate=lambda x: x,
    )


def _cached_compiled_aggregations(query_callback: QueryCallback, site_id: str) -> dict[str, object]:
    global _BI_COMPILED_CACHE
    with _BI_COMPUTER_LOCK:
        now = _time.time()
        if _BI_COMPILED_CACHE is not None and now - _BI_COMPILED_CACHE[0] < _BI_COMPUTER_TTL:
            return _BI_COMPILED_CACHE[1]
        from cmk.bi.compiler import BICompiler
        from cmk.bi.filesystem import get_default_site_filesystem

        bi_fs = get_default_site_filesystem()
        compiler = BICompiler(bi_fs.etc.config, _make_sites_callback(query_callback, site_id))
        compiler.load_compiled_aggregations()
        log.debug(
            "OrbVis BI: compiled %d aggregations from %s (site=%s)",
            len(compiler.compiled_aggregations),
            bi_fs.etc.config,
            site_id,
        )
        compiled: dict[str, object] = compiler.compiled_aggregations
        _BI_COMPILED_CACHE = (now, compiled)
        return compiled


def _cached_computer(query_callback: QueryCallback, site_id: str) -> object:
    """Return a per-call BIComputer over the cached compiled aggregations.

    OrbVis configures one Livestatus connection per OMD site, so a
    process-global compile cache is fine — callbacks always point at the
    same site. The computer itself must NOT be shared (see cache comment).
    """
    from cmk.bi.computer import BIComputer
    from cmk.bi.data_fetcher import BIStatusFetcher

    compiled = _cached_compiled_aggregations(query_callback, site_id)
    return BIComputer(compiled, BIStatusFetcher(_make_sites_callback(query_callback, site_id)))


def cmk_bi_get_aggregations_states(
    query_callback: QueryCallback,
    site_id: str,
    aggregation_names: list[str],
) -> dict[str, dict[str, object]]:
    """Compute current state for a list of BI aggregations via cmk.bi.

    Each *aggregation_name* is the resolved branch title (e.g. ``"Host localhost"``) —
    what Checkmk's ``aggr_single`` view expects as ``aggr_name``. A single bi_config
    aggregation template can produce many branches (one per matching host); we
    identify them by their resolved title.

    Synchronous — callers wrap with asyncio.to_thread(). Per-user permissions
    are honoured because *query_callback* (OrbVis' Livestatus query) injects
    ``AuthUser:`` into every LQL query when run inside ``with_auth_user(...)``.
    """
    if not cmk_bi_available() or not aggregation_names:
        return {}
    try:
        from cmk.bi.computer import BIAggregationFilter

        computer = _cached_computer(query_callback, site_id)
        names = list(aggregation_names)
        # Positional slot 3 is `aggr_names` (resolved branch titles). Slot 2 is
        # `aggr_ids` (bi_config template id) — filling it with the branch title
        # ANDs an unsatisfiable filter and the compute returns an empty list.
        bi_filter = BIAggregationFilter([], [], [], names, [], [])
        results = computer.compute_result_for_filter(bi_filter)  # type: ignore[attr-defined]
        out = _bi_results_to_dict(results)
        log.debug(
            "OrbVis BI: requested %d aggregations, computed %d states",
            len(aggregation_names),
            len(out),
        )
        return out
    except Exception:
        log.warning("cmk.bi compute failed for %s", aggregation_names, exc_info=True)
        return {}


def cmk_bi_get_aggregation_tree(
    query_callback: QueryCallback,
    site_id: str,
    aggregation_name: str,
    max_depth: int,
    scoped: bool = False,
) -> dict[str, Any] | None:
    """Compute the BI aggregation hierarchy as a plain dict tree.

    Mirrors ``cmk.gui.nodevis.aggregation.NodeVisualizationBIDataMapper.consume``
    but truncates at *max_depth* levels (root is depth 0). Returns ``None`` when
    no matching branch exists. Synchronous — wrap with ``asyncio.to_thread``.

    ``scoped=True`` applies the same branch-visibility gate as
    :func:`cmk_bi_list_aggregations` — a contact-scoped user must not pull
    title/structure of an aggregation whose hosts they can't see, even with
    a known/guessed name (the list endpoint alone would only stop enumeration).
    """
    if not cmk_bi_available() or not aggregation_name:
        return None
    try:
        from cmk.bi.computer import BIAggregationFilter

        visible_hosts = _scoped_visible_hosts(query_callback) if scoped else None
        computer = _cached_computer(query_callback, site_id)
        bi_filter = BIAggregationFilter([], [], [], [aggregation_name], [], [])
        results = computer.compute_result_for_filter(bi_filter)  # type: ignore[attr-defined]
        if not isinstance(results, Iterable):
            return None
        for entry in results:
            try:
                _aggr, branches = entry
            except (TypeError, ValueError):
                continue
            for bundle in branches or []:
                instance = getattr(bundle, "instance", None)
                title = str(getattr(getattr(instance, "properties", None), "title", "") or "")
                if title != aggregation_name:
                    continue
                if visible_hosts is not None and not (
                    _branch_required_hosts(instance) & visible_hosts
                ):
                    return None
                return _bundle_to_node(bundle, depth=0, max_depth=max_depth)
        return None
    except Exception:
        log.warning("cmk.bi tree compute failed for %r", aggregation_name, exc_info=True)
        return None


def _bundle_to_node(bundle: Any, depth: int, max_depth: int) -> dict[str, Any]:
    """Recursively convert a NodeResultBundle into the AggregationNode dict shape."""
    from cmk.bi.trees import BICompiledRule

    instance = bundle.instance
    actual = bundle.actual_result
    if isinstance(instance, BICompiledRule):
        name = str(instance.properties.title or "")
        node: dict[str, Any] = {"name": name, "node_type": "bi_aggregator"}
    else:
        host_name = str(getattr(instance, "host_name", "") or "")
        svc = getattr(instance, "service_description", None)
        node = {
            "name": svc or host_name,
            "node_type": "bi_leaf",
            "host_name": host_name or None,
            "service_description": str(svc) if svc else None,
        }
    node["state"] = int(getattr(actual, "state", -1))
    node["in_downtime"] = bool(getattr(actual, "in_downtime", False))
    node["acknowledged"] = bool(getattr(actual, "acknowledged", False))
    node["output"] = str(getattr(actual, "output", "") or "")

    if depth >= max_depth:
        node["children"] = []
        return node
    nested = getattr(bundle, "nested_results", None) or []
    node["children"] = [_bundle_to_node(child, depth + 1, max_depth) for child in nested]
    return node


def _scoped_visible_hosts(query_callback: QueryCallback) -> set[str]:
    """Host names the current livestatus auth scope may see.

    The callback runs inside the caller's auth context, so a contact-scoped
    user gets only their hosts. Rows arrive site-prefixed (``[site, name]``).
    """
    rows = query_callback("GET hosts\nColumns: name\n")
    return {str(row[1]) for row in rows}


def _branch_required_hosts(branch: object) -> set[str]:
    elements: list[Any] = list(getattr(branch, "required_elements", lambda: [])() or [])
    return {str(el[1]) for el in elements}


def cmk_bi_list_aggregations(
    query_callback: QueryCallback, site_id: str, scoped: bool = False
) -> list[dict[str, str]]:
    """List all resolved BI aggregations (one entry per branch).

    Instead of returning the abstract bi_config aggregation templates (which
    contain placeholders like ``Host $HOSTNAME$``), iterate the compiled
    branches and return their resolved titles. The resolved title is what
    Checkmk's ``aggr_single`` view filters by and what users see in the BI UI.

    With ``scoped=True`` (caller runs in a contact-scoped auth context) only
    branches containing at least one host the user may see are listed —
    aggregation titles can be as sensitive as SETUP folder names, and the
    compiled structure itself is site-global (see _bi_query_sync).
    """
    if not cmk_bi_available():
        return []
    try:
        # No computer needed — listing only walks the compiled branches.
        compiled = _cached_compiled_aggregations(query_callback, site_id)
        visible_hosts = _scoped_visible_hosts(query_callback) if scoped else None
        out: list[dict[str, str]] = []
        seen: set[str] = set()
        branch_counts: list[tuple[str, int]] = []
        for aggr_id, compiled_aggr in compiled.items():
            pack_id = str(getattr(compiled_aggr, "pack_id", "") or "")
            # Pull the top-level aggregation function for the editor chip.
            # cmk.bi stores it on the compiled aggregation as either
            # ``aggregation_function`` or ``function`` depending on
            # version; both objects expose a ``.type()`` shortcut so any
            # of those produces a usable label like "worst" / "best" /
            # "count_ok".
            function = ""
            for attr in ("aggregation_function", "function"):
                fn_obj = getattr(compiled_aggr, attr, None)
                if fn_obj is None:
                    continue
                kind = getattr(fn_obj, "type", None)
                if callable(kind):
                    try:
                        function = str(kind())
                    except Exception:
                        function = ""
                elif kind is not None:
                    function = str(kind)
                if function:
                    break
            branches = getattr(compiled_aggr, "branches", []) or []
            branch_counts.append((str(aggr_id), len(branches)))
            for branch in branches:
                title = str(getattr(getattr(branch, "properties", None), "title", "") or "")
                if not title or title in seen:
                    continue
                if visible_hosts is not None and not (
                    _branch_required_hosts(branch) & visible_hosts
                ):
                    continue
                seen.add(title)
                entry: dict[str, str] = {
                    "id": title,
                    "title": title,
                    "pack_id": pack_id,
                }
                if function:
                    entry["function"] = function
                out.append(entry)
        out.sort(key=lambda e: e["title"].lower())
        log.debug(
            "OrbVis BI list_aggregations: %d templates, branches=%s, returned=%d",
            len(compiled),
            branch_counts,
            len(out),
        )
        return out
    except Exception:
        log.warning("cmk.bi list aggregations failed", exc_info=True)
        return []


def _bi_results_to_dict(results: object) -> dict[str, dict[str, object]]:
    """Normalise BIComputer.compute_result_for_filter output into plain dicts.

    The cmk.bi return type is ``Iterable[tuple[BICompiledAggregation,
    list[NodeResultBundle]]]``. Each NodeResultBundle corresponds to a single
    branch — its ``instance.properties.title`` is the resolved aggr_name (and
    the dict key callers requested by). Typed as object here so this module
    can be imported without cmk.* installed.
    """
    out: dict[str, dict[str, object]] = {}
    if not isinstance(results, Iterable):
        return out
    for entry in results:
        try:
            _aggr, branches = entry
        except (TypeError, ValueError):
            continue
        for bundle in branches or []:
            actual = getattr(bundle, "actual_result", None)
            if actual is None:
                continue
            instance = getattr(bundle, "instance", None)
            title = str(getattr(getattr(instance, "properties", None), "title", "") or "")
            if not title:
                continue
            out[title] = {
                "state": int(getattr(actual, "state", -1)),
                "output": str(getattr(actual, "output", "") or ""),
                "acknowledged": bool(getattr(actual, "acknowledged", False)),
                "in_downtime": bool(getattr(actual, "downtime_state", 0)),
            }
    return out
