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
