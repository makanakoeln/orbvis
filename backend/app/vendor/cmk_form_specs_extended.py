# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# Copyright (C) 2025 OrbVis (vendored subset)
"""Vendored subset of ``cmk.rulesets.internal.form_specs._extended``.

OrbVis Pilot consumes only ``DictGroupExtended`` + ``DictionaryGroupLayout``
from CMK's internal form-spec extensions — enough to declare groups that
the FormDictionary renders horizontally / two-column. The upstream
module is not packaged for downstream consumers and not available
across all CMK versions OrbVis supports (e.g. 2.5.0b4 only ships
``ListExtended`` here, the layouted variant came later).

Vendoring keeps the OrbVis backend reproducible across CMK versions
and matches the same strategy used for the frontend
(``frontend/src/vendor/cmk/``). When syncing against a newer CMK
release: re-pull from
``packages/cmk-plugin-apis/cmk/rulesets/internal/form_specs/_extended.py``
in the checkmk repo and keep only the items below.

Note: OrbVis's own ``serialize_form_spec`` reads the ``layout`` field
off our ``OrbDictGroup`` subclass directly, so the type identity here
never has to match CMK's own ``DictGroupExtended`` — the wire output
shape (string layout value) is what matters.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from cmk.rulesets.v1.form_specs import DictGroup


# Mirror the upstream definition verbatim — switching to StrEnum
# would diverge from the file we're tracking against, and ``str, Enum``
# is the form CMK 2.6 itself uses for back-compat with consumers
# already comparing against the string values directly.
class DictionaryGroupLayout(str, Enum):  # noqa: UP042
    horizontal = "horizontal"
    vertical = "vertical"
    two_columns = "two_columns"


@dataclass(frozen=True, kw_only=True)
class DictGroupExtended(DictGroup):  # type: ignore[misc]
    """Group of dictionary elements with an explicit visual ``layout``.

    Mirrors the CMK 2.6 class of the same name. The FormDictionary
    component reads ``layout`` to flip between stacked (vertical) and
    inline (horizontal) renderings of the elements inside the group.
    """

    layout: DictionaryGroupLayout = DictionaryGroupLayout.horizontal
