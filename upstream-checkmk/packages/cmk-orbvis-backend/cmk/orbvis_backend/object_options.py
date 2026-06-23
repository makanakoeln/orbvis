# Copyright (C) 2025 OrbVis - License: GNU General Public License v2
"""Single source of truth for object-option choice lists.

The same line-style / map-type catalogues are referenced from two
places that used to drift independently:

- ``app/form_specs/global_settings.py`` — Global Settings FormSpec dropdowns.
- ``frontend/src/utils/dropdownOptions.ts`` — per-object EditPanel + create
  modals.

Defining the names here and serving them via ``GET /api/v1/object-options``
makes the backend the canonical owner: the FormSpec builder reads from
this module, and the frontend store ``stores/objectOptions.ts`` fetches
the list at boot. Display titles stay backend-only fallbacks; the
frontend overlays its own i18n keys so existing translations keep
working without a round-trip.
"""

from __future__ import annotations

# Order matches the historical dropdown order in the EditPanel — the
# "Simple line" / "Dashed" pair is the most-used set, the arrow variants
# come below as a related cluster.
LINE_STYLES: tuple[tuple[str, str], ...] = (
    ("plain", "Simple line"),
    ("dashed", "Dashed"),
    ("arrow_end", "Arrow at end"),
    ("arrow_start", "Arrow at start"),
    ("arrow_both", "Arrows on both ends"),
    ("arrow_inward", "Arrows pointing inward"),
)
