#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Role row dataclass — mirrors the ``roles`` table from core/schema.sql."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Role:
    name: str = ""
    role_id: int = 0
    permissions: list[Permission] = field(default_factory=list)
    users: list[User] = field(default_factory=list)

    def __repr__(self) -> str:
        return f"<Role id={self.role_id} name={self.name!r}>"


from cmk.orbvis_backend.models.permission import Permission
from cmk.orbvis_backend.models.user import User
