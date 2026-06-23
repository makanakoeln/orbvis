# Copyright (C) 2025 OrbVis - License: GNU General Public License v2
"""Server-side validation for FormSpec submissions.

Delegates to the visitor registry in :mod:`app.form_specs._visitors`,
where each FormSpec type owns both serialise and validate. This is the
same one-visitor-per-type pattern CMK uses in
``cmk.gui.form_specs.visitors._base.FormSpecVisitor``.
"""

from __future__ import annotations

from cmk.orbvis_backend.form_specs.serialize import FormSpecValidationMessage

from cmk.rulesets.v1.form_specs import FormSpec


def validate_form_data(
    spec: FormSpec[object],
    data: object,
) -> list[FormSpecValidationMessage]:
    import app.form_specs._visitors  # noqa: F401 — side-effect: registers visitors
    from cmk.orbvis_backend.form_specs._registry import get_visitor

    return list(get_visitor(spec).validate(spec, data, []))
