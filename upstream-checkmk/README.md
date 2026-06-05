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
in place. The frontend package is still a placeholder.

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

## Open questions (to clarify before Stage 6 starts)

1. Tailwind in the built-in bundle? cmk-frontend-vue uses CMK SCSS tokens —
   does legal/design accept Tailwind alongside?
2. Backend URL of the external OrbVis backend: how does the built-in frontend
   discover it? OMD site-setting, env var, configuration UI in `cmk/gui/orbvis/`?
3. Node version for the external `frontend/` tree when the built-in goes to
   Node 22+ — upgrade both or keep the external tree at 18+?
