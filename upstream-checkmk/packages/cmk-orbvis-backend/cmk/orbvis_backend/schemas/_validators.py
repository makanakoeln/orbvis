#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Shared validators for user-supplied URL fields on maps/presentations."""

from __future__ import annotations

import re

# Allowlist instead of a scheme blocklist: browsers strip ASCII control
# characters when parsing URLs, so "java\tscript:alert(1)" bypasses any
# startswith("javascript:") check yet still executes on click. Rejecting
# control characters outright and allowlisting schemes closes that class.
# Beyond the web schemes, monitoring maps traditionally link remote-access
# handlers on host objects (NagVis heritage) — those are user-mediated OS
# handlers, not script-capable, so they stay allowed.
# Keep in sync with SAFE_URL_SCHEMES in frontend/src/utils/sanitize.ts.
_ALLOWED_URL_SCHEMES = frozenset(
    {"http", "https", "mailto", "tel", "ssh", "telnet", "rdp", "vnc", "ftp"}
)
_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")
_URL_SCHEME = re.compile(r"^([a-zA-Z][a-zA-Z0-9+.\-]*):")


def validate_user_url(value: str | None) -> str | None:
    """Allow scheme-less (relative) URLs plus the allowlisted schemes."""
    if not value:
        return value
    if len(value) > 4096:
        raise ValueError("URL too long")
    s = value.strip()
    if _CONTROL_CHARS.search(s):
        raise ValueError("URL must not contain control characters")
    m = _URL_SCHEME.match(s)
    if m and m.group(1).lower() not in _ALLOWED_URL_SCHEMES:
        raise ValueError(f"URL scheme {m.group(1)!r} is not allowed")
    return s


def coerce_user_url(value: object) -> object:
    """Sanitize now-invalid URLs to ``None`` so legacy maps still load.

    Read-side companion to ``validate_user_url``, same contract as
    ``_coerce_color``: stored JSON may pre-date the allowlist; dropping the
    offending URL keeps the map loadable while API saves stay strict.
    """
    if value is None or value == "":
        return value
    if not isinstance(value, str):
        return None
    try:
        return validate_user_url(value)
    except ValueError:
        return None
