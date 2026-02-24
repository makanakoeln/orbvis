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
