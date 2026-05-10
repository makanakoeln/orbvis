# OrbVis – Checkmk Builtin Readiness Audit

This document tracks deviations between OrbVis and Checkmk's conventions
that would block or impede inclusion of OrbVis as a **builtin plugin
shipped with Checkmk 2.6**. Generated 2026-05-10 against CMK 2.5/2.6
source trees.

## Critical blockers

### 1. Backend architecture mismatch
- **OrbVis:** Separate FastAPI/uvicorn daemon, async SQLAlchemy, own
  systemd service.
- **CMK:** Monolithic mod_python/werkzeug GUI; builtin modules import +
  register inside the single Apache process.
- **Action for builtin:** Refactor backend to live inside CMK's GUI
  process, expose endpoints via CMK's own werkzeug routes. The
  separate-daemon model is incompatible with OMD deployment.

### 2. User / auth / permission stack
- **OrbVis:** Standalone User/Role/Permission ORM in FastAPI, JWT
  tokens, local password hashing, custom `orbvis.view_*` permissions.
- **CMK:** `cmk.gui.userdb` for users, `cmk.gui.permissions` for RBAC,
  contact-group based visibility.
- **Action for builtin:** Drop OrbVis's user/auth layer entirely; trust
  CMK's authenticated session. Map board ownership/visibility onto
  contact groups (or custom attributes linked to them).

### 3. OMD deployment integration
- **OrbVis:** Custom `orbvis-setup` script, separate venv, separate
  apache snippet, separate DB.
- **CMK:** Builtin modules deploy as part of the site's Python env and
  Apache process; persistent data lives under `$OMD_ROOT/local/share/`
  (filesystem) or in CMK's config domain system.
- **Action for builtin:** Remove the separate daemon, serve via CMK's
  werkzeug, persist boards as JSON files (already supported as
  fallback) or via CMK's config domain.

## Should-fix (recommended for clean builtin inclusion)

### 4. Permission registration pattern
- **OrbVis:** `cmk_plugins/.../orbvis_permissions.py` calls
  `declare_permission_section()` / `declare_permission()` /
  `declare_dynamic_permissions()` at import time, with try/except
  ImportError shims for 2.4/2.5/2.6.
- **CMK builtin:** `register(permission_section_registry,
  permission_registry)` callback pattern (see
  `cmk.gui.wato._permissions.register()`,
  `cmk.gui.nagvis.register()`).
- **Action:** Move into a clean `cmk.gui.orbvis.__init__.register()`
  function. Drop the version bridges.

### 5. Frontend tokens / Tailwind
- **OrbVis:** Tailwind v4 + custom `--color-state-*` / `--color-mod-*`
  tokens layered on top of CMK's CSS variables.
- **CMK builtin:** Pure CSS-variable model; tokens come from
  `cmk-frontend-vue/src/assets/{colors,variables}.css`.
- **Action:** Drop Tailwind, port styles to CMK tokens only. Move
  components into `packages/cmk-orbvis-frontend/` alongside the rest of
  `cmk-frontend-vue`.

### 6. Vendored CMK components
- **OrbVis:** `frontend/src/vendor/cmk/` carries copies of CmkButton,
  CmkSwitch, CmkColorPicker, CmkIcon, etc.
- **CMK builtin:** Import from `@cmk/cmk-frontend-vue` (or the
  monorepo's shared package).
- **Action:** Remove the vendor folder once OrbVis lives in the same
  monorepo as `cmk-frontend-vue`.

### 7. Livestatus client
- **OrbVis:** Custom async Livestatus implementation in
  `backend/app/connections/livestatus.py`.
- **CMK:** `cmk.livestatus_client.MultiSiteConnection` (in
  `packages/cmk-livestatus-client/`).
- **Action:** Migrate to the official client when 2.6 finalises its
  async-friendly API; contribute the async wrapper upstream if needed.
  *Custom graphing-metadata extraction is fine to keep.*

### 8. Module-tree placement
- **OrbVis today:** `cmk_plugins/cmk/gui/plugins/{sidebar,wato}/orbvis_*.py`
  (plugin-mode layout) plus a `upstream-checkmk/cmk/gui/orbvis/`
  staging tree.
- **CMK builtin:** `cmk/gui/orbvis/{__init__.py, …}` for the GUI side
  and `packages/cmk-orbvis-frontend/` for the Vue bundle.
- **Action:** Real builtin inclusion = merging into Checkmk's source
  tree, not staging in `upstream-checkmk/`.

## Non-issues

- **Type annotations** are already strict (mypy `Stage 3`, pydantic
  plugin), exceeding CMK's baseline.
- **Ruff config** already extends Checkmk's rule set.
- **Snapin/sidebar registration** uses `@snapin_registry.register`
  correctly.

## Roadmap summary

| Priority | Item | Effort |
|---------|------|--------|
| Blocker | Merge FastAPI backend into CMK GUI process | XL |
| Blocker | Replace user/role/permission stack with `cmk.gui.userdb` + `cmk.gui.permissions` | L |
| Blocker | Drop separate daemon, serve via CMK's werkzeug | L |
| Should | Permission registry-callback refactor | S |
| Should | Frontend monorepo port (drop Tailwind) | L |
| Should | Drop vendored components | S (after monorepo port) |
| Should | Migrate to `cmk.livestatus_client` | M |

---

For the **non-builtin / MKP-shipped** mode that is the current focus,
none of these items are blocking. They are recorded here so that the
2.6 builtin upstream effort starts with a known punch-list rather than
a fresh audit.
