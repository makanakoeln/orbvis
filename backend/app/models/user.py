"""User row dataclass — mirrors the ``users`` table from core/schema.sql."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class User:
    name: str = ""
    password: str = ""
    is_active: bool = True
    is_admin: bool = False
    must_change_password: bool = False
    theme: str = "system"
    language: str = "en"
    user_id: int = 0
    roles: list[Role] = field(default_factory=list)

    def __repr__(self) -> str:
        return f"<User id={self.user_id} name={self.name!r}>"


from app.models.role import Role
