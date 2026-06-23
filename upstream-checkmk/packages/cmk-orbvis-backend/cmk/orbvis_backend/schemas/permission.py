#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Permission schemas."""

from pydantic import BaseModel, Field


class PermissionBase(BaseModel):
    mod: str = Field(..., max_length=100)
    act: str = Field(..., max_length=100)
    obj: str = Field("*", max_length=200)


class PermissionCreate(PermissionBase):
    pass


class PermissionRead(PermissionBase):
    perm_id: int

    model_config = {"from_attributes": True}
