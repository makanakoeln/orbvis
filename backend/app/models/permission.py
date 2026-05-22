"""Permission row dataclass — NagVis mod/act/obj triplet."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Permission:
    mod: str = ""
    act: str = ""
    obj: str = "*"
    perm_id: int = 0

    def __repr__(self) -> str:
        return f"<Permission {self.mod}/{self.act}/{self.obj}>"
