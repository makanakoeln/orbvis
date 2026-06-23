#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Permission row dataclass — NagVis mod/act/obj triplet."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Permission:
    mod: str = ""
    act: str = ""
    obj: str = "*"
    perm_id: int = 0

    def __repr__(self) -> str:
        return f"<Permission {self.mod}/{self.act}/{self.obj}>"
