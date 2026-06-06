# upstream-checkmk/

Transfer-ready skeleton of the OrbVis code that is intended to ship
**built-in** with Checkmk in the future. This directory mirrors the
target paths in `~/git/checkmk/` 1:1, so the eventual merge is a simple
`rsync` per sub-tree — see the `ship-to-checkmk` make-target (added in
Stage 7).

## Target paths

| Path in this skeleton                      | Target in `~/git/checkmk/`                |
|--------------------------------------------|-------------------------------------------|
| `cmk/gui/orbvis/`                          | `cmk/gui/orbvis/`                         |
| `packages/cmk-orbvis-frontend/`            | `packages/cmk-orbvis-frontend/`           |
| `tests/unit/cmk/gui/orbvis/`               | `tests/unit/cmk/gui/orbvis/`              |

## Current status

Stage 6a is done: `cmk/gui/orbvis/` and `tests/unit/cmk/gui/orbvis/` carry
the real GUI integration (permissions, dynamic per-board permissions,
sidebar snap-in) ported from `cmk_plugins_23/` — without the 2.3/2.4/2.5
compatibility bridges, modelled 1:1 on `cmk/gui/nagvis/`. Checkmk GPLv2
headers and `BUILD` files (shapes verified against the nagvis targets) are
in place.

Stage 6b/6c is done: `packages/cmk-orbvis-frontend/` carries the real
package — configs modelled on cmk-frontend-vue, `src/` generated from
`frontend/src/` by `scripts/sync-upstream-frontend.sh` (drift check:
`npm run drift-check:upstream` in `frontend/`), deployment via `pkg_tar`
to `share/check_mk/web/htdocs/cmk-orbvis-frontend/` (NOT a wheel — see
the package README). Verified in real merge topology (temp copy into
`~/git/checkmk/` + pnpm workspace entry): `vite build`, `vue-tsc` and
all 150 vitest tests green against current cmk-frontend-vue master.
Verification caveat: `cmk-shared-typing/typescript/` was generated with
`json2ts` directly (icon, vue_formspec_components, user_frontend_config,
configuration_entity); `openapi_internal` needs the Bazel pipeline and
was covered by a minimal hand-written subset.

Explicitly **not** set yet:

- `LICENSE` — the upstream file is pulled in at merge time.
- The main menu entry: upstream needs a `NavItemIdEnum` member in
  `cmk/shared_typing` plus a `main_menu_registry` entry — both outside this
  additive sub-tree, to be done as a small upstream patch at merge time
  (the MKP's `orbvis_menu.py` monkeypatching is not upstream material).

Required merge-time changes outside this sub-tree:

- `cmk/gui/community_registration.py`: call
  `orbvis.register(permission_section_registry, permission_registry, snapin_registry)`
  next to the existing `nagvis.register(...)` call.
- `tests/unit/cmk/gui/plugins/sidebar/test_snapins.py`: add
  `"orbvis_boards"` to the expected snap-in list.

## How the built-in delivery relates to the external MKP

OrbVis ships on two tracks after Stage 6 is complete:

- **built-in**: code lives here, intended to be merged into the Checkmk
  source tree, owned by Checkmk GmbH under GPLv2.
- **external MKP / standalone**: code continues to live under `backend/`,
  `frontend/`, `cmk_plugins/`, `cmk_plugins_23/` at the repo root, pulled
  into MKP archives the existing way.

The two tracks coexist; they are not alternatives. Bug fixes are cherry-picked
between them where applicable.

## Resolved questions

1. ~~Tailwind in the built-in bundle?~~ — Tailwind was removed from the
   frontend entirely (CMK design tokens).
2. ~~Backend URL discovery?~~ — site-local like NagVis (user decision
   2026-06-05): the per-site Apache config proxies `/api` to the
   site-local backend; no URL configuration surface needed.
3. ~~Node version for the external tree?~~ — the external `frontend/`
   stays on its current floor for 2.3–2.5 MKP compat; only
   `packages/cmk-orbvis-frontend/` targets Node 22+/Vite 7/TS 6.
