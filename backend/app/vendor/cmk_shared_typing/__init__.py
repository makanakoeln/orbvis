# Copyright (C) 2025 OrbVis - License: GNU General Public License v2
"""Vendored snapshot of ``cmk.shared_typing`` (vue-formspec subset only).

Built from the auto-generated output of
``packages/cmk-shared-typing/`` in the Checkmk repository — the canonical
single source of truth for the FormSpec wire format that both the Python
backend and the cmk-frontend-vue dispatcher agree on.

Why vendoring is needed:
- The shared-typing package is generated via Bazel; raw checkmk master
  doesn't ship a ready-to-import ``.py`` file.
- OrbVis ships as MKP for CMK 2.3 / 2.4 / 2.5 where the package layout
  differs (cmk.shared_typing only landed reliably in 2.4+).
- Built-in OrbVis on CMK ≥ 2.5 prefers the real ``cmk.shared_typing``
  module — the shim in :mod:`app.form_specs._wire_types` tries the
  upstream import first and falls back to this vendor only on
  ``ImportError``.

To refresh: copy from the latest stable OMD site, e.g.
``/omd/versions/2.6.0-*/lib/python3.13/site-packages/cmk/shared_typing/vue_formspec_components.py``.
"""
