"""User model."""

from __future__ import annotations

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import relationship, Mapped, mapped_column

from app.core.database import Base
from app.models.role import users2roles


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    roles: Mapped[list["Role"]] = relationship(
        "Role", secondary=users2roles, back_populates="users", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<User id={self.user_id} name={self.name!r}>"
