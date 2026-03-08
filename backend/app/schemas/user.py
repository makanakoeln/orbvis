"""User schemas."""

from pydantic import BaseModel, Field, model_validator


class RoleRef(BaseModel):
    role_id: int
    name: str

    model_config = {"from_attributes": True}


class PermissionRef(BaseModel):
    perm_id: int
    mod: str
    act: str
    obj: str

    model_config = {"from_attributes": True}


class UserBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    is_active: bool = True
    is_admin: bool = False
    must_change_password: bool = False
    theme: str = "system"


class UserCreate(UserBase):
    password: str = Field(..., min_length=6)


class UserUpdate(BaseModel):
    name: str | None = None
    password: str | None = Field(None, min_length=6)
    is_active: bool | None = None
    is_admin: bool | None = None
    must_change_password: bool | None = None
    theme: str | None = None


class UserRead(UserBase):
    user_id: int
    roles: list[RoleRef] = []
    permissions: list[PermissionRef] = []

    model_config = {"from_attributes": True}

    @model_validator(mode="before")
    @classmethod
    def _collect_permissions(cls, data: object) -> object:
        """Flatten permissions from all assigned roles into a deduplicated list."""
        if isinstance(data, dict):
            return data
        if not hasattr(data, "roles"):
            return data
        seen: set[int] = set()
        perms: list[object] = []
        for role in data.roles or []:
            for perm in role.permissions or []:
                if perm.perm_id not in seen:
                    seen.add(perm.perm_id)
                    perms.append(perm)
        return {
            "user_id": data.user_id,
            "name": data.name,
            "is_active": data.is_active,
            "is_admin": data.is_admin,
            "must_change_password": data.must_change_password,
            "theme": getattr(data, "theme", "system"),
            "roles": data.roles or [],
            "permissions": perms,
        }
