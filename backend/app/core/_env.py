"""Minimal .env loader — replaces pydantic-settings' env_file= machinery.

Process environment wins over the file (setdefault), matching pydantic-settings'
precedence. Grammar is intentionally tiny since orbvis-setup writes the file
under our control: KEY=VALUE lines, # comments, optional outer single/double
quotes — no multi-line values, no variable expansion, no escape sequences.
"""

from __future__ import annotations

import os


def load_env_file(path: str | os.PathLike[str]) -> None:
    try:
        with open(path, encoding="utf-8") as f:
            lines = f.readlines()
    except FileNotFoundError:
        return

    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, sep, value = line.partition("=")
        if not sep:
            continue
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        if key:
            os.environ.setdefault(key, value)
