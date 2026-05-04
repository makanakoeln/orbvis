"""Shared Pydantic/FastAPI type aliases for v1 endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import Path

# Board names end up as filenames (under boards_dir) and as path components
# in Checkmk permission lookups. Restricting the character set here prevents
# path traversal and odd permission-key lookups before the value reaches any
# business logic.
BoardName = Annotated[
    str,
    Path(pattern=r"^[a-zA-Z0-9_\-]+$", min_length=1, max_length=100),
]
