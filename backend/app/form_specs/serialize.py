# Copyright (C) 2025 OrbVis - License: GNU General Public License v2
"""FormSpec → JSON for the vendored frontend dispatcher.

Output shape matches :mod:`cmk.gui.form_specs.visitors` so the vendored
frontend components can render it 1:1 with the upstream FormSpec stack.

The actual per-type logic lives in :mod:`app.form_specs._visitors`,
which registers a visitor for each supported FormSpec class. This module
keeps the public surface (``OrbColorString``, ``OrbDictGroup``,
``FormSpecValidationMessage``, ``serialize_form_spec``) so existing
imports keep working.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.vendor.cmk_form_specs_extended import DictGroupExtended, DictionaryGroupLayout

from cmk.rulesets.v1.form_specs import FormSpec, String

if TYPE_CHECKING:
    from app.form_specs._wire_types import AnyWireFormSpec


# cmk.rulesets.v1.form_specs ships untyped (.pyi-less) for downstream
# consumers, so mypy sees `String` as `Any`; the subclass is legitimate at
# runtime — that's exactly how upstream defines its own form-specs internally.
class OrbColorString(String):  # type: ignore[misc]
    """String FormSpec rendered with a native color picker in the frontend.

    Storage and validation stay String — keeping API + Pydantic shape stable —
    but the wire type is rewritten to ``orb_color`` so the dispatcher swaps
    in FormOrbColor.vue. CMK has no first-party color FormSpec (verified
    against cmk-frontend-vue 2.5), so this is the smallest add-on that
    keeps the rest of the FormSpec stack unmodified.
    """


@dataclass(frozen=True, kw_only=True)
class OrbDictGroup(DictGroupExtended):
    """``DictGroupExtended`` + explicit ``key`` for OrbVis FormSpecs.

    Inherits ``layout`` (horizontal/vertical/two_columns) from the
    vendored ``DictGroupExtended``, but flips the default back to
    ``vertical`` — most OrbVis groups want stacked sections, and only
    a small number (e.g. label X/Y offsets) opt into horizontal.

    CMK identifies groups by ``repr(title)+repr(help_text)`` in its
    visitor — fragile when titles repeat or are empty — so ``key``
    stays as an OrbVis-side field for the sidebar mapping in
    GlobalSettingsView (board_defaults, object_appearance, …).
    """

    layout: DictionaryGroupLayout = DictionaryGroupLayout.vertical
    key: str | None = None


@dataclass(frozen=True)
class FormSpecValidationMessage:
    location: list[str]
    message: str
    invalid_value: object | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "location": list(self.location),
            "message": self.message,
            "invalid_value": self.invalid_value,
        }


def serialize_form_spec(spec: FormSpec[object]) -> AnyWireFormSpec:
    # Lazy import: ``_visitors`` imports from this module for OrbColorString,
    # so we wait until first call to avoid the circular import at module load.
    import app.form_specs._visitors  # noqa: F401 — side-effect: registers visitors
    from app.form_specs._registry import get_visitor

    return get_visitor(spec).serialize(spec)
