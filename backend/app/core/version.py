"""Resolve the application version from the bundled VERSION file."""

from pathlib import Path

_candidates = [
    Path(__file__).parent.parent / "VERSION",
    Path(__file__).parent.parent.parent.parent / "VERSION",
    Path(__file__).parent.parent.parent / "VERSION",
]
APP_VERSION = next((p.read_text().strip() for p in _candidates if p.is_file()), "0.0.0")
