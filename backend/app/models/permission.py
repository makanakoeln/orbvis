"""Permission model – mod/act/obj triplet, mirrors legacy NagVis schema."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.role import roles2perms

if TYPE_CHECKING:
    from app.models.role import Role


class Permission(Base):
    __tablename__ = "permissions"
    __table_args__ = (UniqueConstraint("mod", "act", "obj", name="uq_perm_triplet"),)

    perm_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    mod: Mapped[str] = mapped_column(String(100), nullable=False)
    act: Mapped[str] = mapped_column(String(100), nullable=False)
    obj: Mapped[str] = mapped_column(String(200), nullable=False, default="*")

    roles: Mapped[list[Role]] = relationship(
        "Role", secondary=roles2perms, back_populates="permissions", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Permission {self.mod}/{self.act}/{self.obj}>"
