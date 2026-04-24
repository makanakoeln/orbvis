"""Built-in OrbVis GUI integration for Checkmk (placeholder — populated in Stage 6).

Will expose a ``register(permission_section_registry, permission_registry,
snapin_registry_)`` entry point following the pattern established by
``cmk.gui.nagvis``. The real implementation ports from ``cmk_plugins_23/``
without the 2.3/2.4/2.5-compatibility bridges.
"""

from __future__ import annotations


def register() -> None:
    """Entry point — will be wired up to Checkmk's plugin registries in Stage 6."""
