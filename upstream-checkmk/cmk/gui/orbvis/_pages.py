#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Serve the Checkmk Maps single-page app shell.

One checkmk page renders the SPA inside the regular Checkmk chrome and loads the
``cmk-orbvis-frontend`` bundle from the web htdocs via its Vite ``.manifest.json``
(same mechanism as ``cmk-frontend-vue``). The hash router decides which view to
show; the per-site API/SSE base is injected so a single shared bundle serves
every site.
"""

import json
from collections.abc import Mapping
from functools import lru_cache
from typing import Any, NamedTuple

import cmk.utils.paths
from cmk.ccc.site import url_prefix
from cmk.gui.breadcrumb import make_simple_page_breadcrumb
from cmk.gui.exceptions import MKAuthException
from cmk.gui.header import make_header
from cmk.gui.htmllib.html import html
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.main_menu import main_menu_registry
from cmk.gui.page_menu import PageMenu
from cmk.gui.pages import PageContext, PageEndpoint, PageRegistry

_BUNDLE = "cmk-orbvis-frontend"


class _Manifest(NamedTuple):
    main: str
    stylesheets: list[str]


@lru_cache
def _load_manifest() -> _Manifest:
    base = cmk.utils.paths.web_dir / "htdocs" / _BUNDLE
    with (base / ".manifest.json").open() as fo:
        manifest = json.load(fo)
    main = f"{_BUNDLE}/{manifest['src/main.ts']['file']}"
    return _Manifest(main, _collect_stylesheets(manifest, "src/main.ts"))


def _collect_stylesheets(
    manifest: Mapping[str, Any], entry_key: str, _seen: set[str] | None = None
) -> list[str]:
    """Recursively walk the import graph to collect every stylesheet."""
    seen = _seen if _seen is not None else set()
    if entry_key in seen:
        return []
    seen.add(entry_key)
    entry = manifest[entry_key]
    stylesheets: list[str] = []
    for imported in entry.get("imports", []):
        stylesheets += _collect_stylesheets(manifest, imported, seen)
    for stylesheet in entry.get("css", []):
        if stylesheet not in stylesheets:
            stylesheets.append(stylesheet)
    return stylesheets


def register(page_registry: PageRegistry) -> None:
    page_registry.register(PageEndpoint("orbvis", page_orbvis))


def page_orbvis(ctx: PageContext) -> None:
    if not user.may("orbvis.use"):
        raise MKAuthException(_("You are not allowed to use Checkmk Maps."))

    title = _("Maps")
    breadcrumb = make_simple_page_breadcrumb(main_menu_registry.menu_monitoring(), title)
    make_header(
        html,
        title,
        breadcrumb,
        PageMenu(breadcrumb=breadcrumb),
        debug=ctx.config.debug,
        lang=user.language,
        inject_js_profiling_code=ctx.config.inject_js_profiling_code,
        load_frontend_vue=ctx.config.load_frontend_vue,
        custom_style_sheet=ctx.config.custom_style_sheet,
        screenshotmode=ctx.config.screenshotmode,
        inline_help_as_text=user.inline_help_as_text,
        hide_suggestions=not user.get_tree_state("suggestions", "all", True),
        user_role_ids=user.role_ids,
    )

    # Per-site API/SSE base for the shared bundle (read by resolveDeploymentBase).
    html.javascript(f"window.__ORBVIS_BASE__ = {json.dumps(url_prefix() + 'orbvis')};")
    html.open_div(id_="app")
    html.close_div()

    manifest = _load_manifest()
    html.javascript_file(manifest.main, type_="module")
    for stylesheet in manifest.stylesheets:
        html.stylesheet(f"{_BUNDLE}/{stylesheet}")

    html.footer()
