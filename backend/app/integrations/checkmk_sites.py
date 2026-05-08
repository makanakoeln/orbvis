"""Discover Checkmk distributed-monitoring site configuration.

When OrbVis runs inside a Checkmk OMD site, this module loads
``etc/check_mk/multisite.d/sites.mk`` and returns the live site specs in the
shape expected by :class:`livestatus.MultiSiteConnection`. Returns ``None`` to
signal "stay on the single-site fast path" — when not in an OMD site, when
sites.mk is missing or unparseable, or when only the local site is configured.

The normalisation helpers ``_encode_socket_for_livestatus`` and
``_site_config_for_livestatus`` are direct ports of their counterparts in
``cmk/gui/sites.py``. ``_filter_enabled`` and ``_is_single_local_site`` are
ports of ``cmk.gui.site_config.{enabled_sites,is_single_local_site}``. We
copy them rather than import:
- ``cmk.gui.sites`` imports flask/g/active_config at module top and cannot be
  imported outside a GUI request context.
- ``cmk.gui.site_config.enabled_sites`` / ``is_single_local_site`` changed
  signatures across versions: 2.3/2.4 take no args and read the global
  ``active_config.sites``; 2.5+ take the site-config mapping explicitly.
The bodies are trivial and stable across the WATO site-spec contract.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.integrations import checkmk as _cmk_integration

log = logging.getLogger(__name__)


def _sites_mk_path() -> Path | None:
    if not settings.checkmk_omd_root:
        return None
    return Path(settings.checkmk_omd_root) / "etc" / "check_mk" / "multisite.d" / "sites.mk"


def sites_mk_mtime() -> float:
    """Return mtime of sites.mk for cache invalidation, or 0.0 when absent."""
    p = _sites_mk_path()
    if p is None:
        return 0.0
    try:
        return p.stat().st_mtime if p.is_file() else 0.0
    except OSError:
        return 0.0


def _encode_socket_for_livestatus(
    site_id: str, site_spec: dict[str, Any], livestatus_unix_socket: str
) -> str:
    """Port of cmk.gui.sites.encode_socket_for_livestatus (stable 2.3-2.5+)."""
    socket_spec = site_spec["socket"]
    if site_spec.get("proxy") is not None:
        return f"unix:{livestatus_unix_socket}proxy/{site_id}"
    if socket_spec[0] == "local":
        return f"unix:{livestatus_unix_socket}"
    if socket_spec[0] == "unix":
        return f"{socket_spec[0]}:{socket_spec[1]['path']}"
    if socket_spec[0] in ("tcp", "tcp6"):
        return f"{socket_spec[0]}:{socket_spec[1]['address'][0]}:{socket_spec[1]['address'][1]}"
    raise NotImplementedError(f"Unknown socket family: {socket_spec[0]!r}")


def _site_config_for_livestatus(
    site_id: str, site_spec: dict[str, Any], livestatus_unix_socket: str
) -> dict[str, Any]:
    """Port of cmk.gui.sites._site_config_for_livestatus (stable 2.3-2.5+).

    Preserves the original spec (including ``status_host`` for dead-site
    detection and ``proxy`` for liveproxy routing) and adds the encoded socket
    plus cache/tls hints expected by ``MultiSiteConnection``.
    """
    copied = dict(site_spec)
    proxy = site_spec.get("proxy")
    if proxy is not None:
        copied["cache"] = proxy.get("cache", True) if isinstance(proxy, dict) else True
    else:
        sock = site_spec.get("socket")
        if isinstance(sock, tuple) and sock[0] in ("tcp", "tcp6"):
            copied["tls"] = sock[1]["tls"]
    copied["socket"] = _encode_socket_for_livestatus(site_id, site_spec, livestatus_unix_socket)
    return copied


def _filter_enabled(site_configs: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Port of cmk.gui.site_config.enabled_sites — version-agnostic.

    2.3/2.4 read ``active_config.sites`` implicitly; 2.5+ take the mapping as
    an argument. The body is trivial: drop entries flagged ``disabled``.
    """
    return {
        site_id: dict(spec)
        for site_id, spec in site_configs.items()
        if not spec.get("disabled", False)
    }


def _is_single_local_site(sites: dict[str, dict[str, Any]], livestatus_unix_socket: str) -> bool:
    """Port of cmk.gui.site_config.is_single_local_site — version-agnostic."""
    if len(sites) > 1:
        return False
    if not sites:
        return True
    spec = next(iter(sites.values()))
    sock = spec.get("socket")
    if not isinstance(sock, tuple):
        return False
    if sock[0] == "local":
        return True
    if sock[0] == "unix":
        path = sock[1].get("path") if isinstance(sock[1], dict) else None
        return path == livestatus_unix_socket
    return False


def load_sites() -> dict[str, dict[str, Any]] | None:
    """Return enabled Checkmk site configurations for ``MultiSiteConnection``.

    Returns ``None`` (= keep the single-socket fast path) when not in an OMD
    site, when sites.mk is missing or unparseable, when cmk.* modules aren't
    importable, or when only the local site is enabled.
    """
    p = _sites_mk_path()
    if p is None or not p.is_file():
        return None
    try:
        raw = _cmk_integration.exec_mk_file(p, {"sites": {}}).get("sites", {})
    except Exception as exc:
        log.error("Failed to parse %s: %s", p, exc, exc_info=True)
        return None
    if not isinstance(raw, dict) or not raw:
        return None

    if not _cmk_integration.available:
        return None
    try:
        from cmk.utils.paths import livestatus_unix_socket
    except ImportError as exc:
        log.warning("cmk.utils.paths not importable: %s", exc)
        return None

    enabled = _filter_enabled(raw)
    if _is_single_local_site(enabled, str(livestatus_unix_socket)):
        return None

    out: dict[str, dict[str, Any]] = {}
    for site_id, spec in enabled.items():
        try:
            out[str(site_id)] = _site_config_for_livestatus(
                str(site_id), dict(spec), str(livestatus_unix_socket)
            )
        except Exception as exc:
            log.warning("Skipping site %r — invalid spec: %s", site_id, exc)
    return out or None
