#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Role schemas."""

from pydantic import BaseModel, Field


class PermissionRef(BaseModel):
    perm_id: int
    mod: str
    act: str
    obj: str

    model_config = {"from_attributes": True}


class RoleBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)


class RoleCreate(RoleBase):
    pass


class RoleRead(RoleBase):
    role_id: int
    permissions: list[PermissionRef] = []

    model_config = {"from_attributes": True}
