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


from app.models.permission import Permission
from app.models.user import User
