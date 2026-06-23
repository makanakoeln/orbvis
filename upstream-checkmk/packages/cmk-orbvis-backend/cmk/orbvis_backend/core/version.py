#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Resolve the application version from the bundled VERSION file."""

from pathlib import Path

_candidates = [
    Path(__file__).parent.parent / "VERSION",
    Path(__file__).parent.parent.parent.parent / "VERSION",
    Path(__file__).parent.parent.parent / "VERSION",
]
APP_VERSION = next((p.read_text().strip() for p in _candidates if p.is_file()), "0.0.0")
