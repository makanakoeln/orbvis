"""User schemas."""

from pydantic import BaseModel, Field


class RoleRef(BaseModel):
    role_id: int
    name: str

    model_config = {"from_attributes": True}


class UserBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    is_active: bool = True
    is_admin: bool = False
    must_change_password: bool = False


class UserCreate(UserBase):
    password: str = Field(..., min_length=6)


class UserUpdate(BaseModel):
    name: str | None = None
    password: str | None = Field(None, min_length=6)
    is_active: bool | None = None
    is_admin: bool | None = None
    must_change_password: bool | None = None


class UserRead(UserBase):
    user_id: int
    roles: list[RoleRef] = []

    model_config = {"from_attributes": True}
