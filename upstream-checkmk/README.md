# upstream-checkmk/

Transfer-ready skeleton of the OrbVis code that will ship **built-in** with
Checkmk (starting with 2.6.0). This directory mirrors the target paths in
`~/git/checkmk/` 1:1, so the eventual merge is a simple `rsync` per
sub-tree — see the `ship-to-checkmk` make-target (added in Stage 7).

## Target paths

| Path in this skeleton                      | Target in `~/git/checkmk/`                |
|--------------------------------------------|-------------------------------------------|
| `cmk/gui/orbvis/`                          | `cmk/gui/orbvis/`                         |
| `packages/cmk-orbvis-frontend/`            | `packages/cmk-orbvis-frontend/`           |
| `tests/unit/cmk/gui/orbvis/`               | `tests/unit/cmk/gui/orbvis/`              |

## Current status — skeleton only

Stage 6 of the rollout plan ports the real code from the external OrbVis
tree into these directories. Until then the Python modules are empty stubs
(so mypy strict / ruff still pass) and the frontend package is a placeholder.

Explicitly **not** set yet:

- Copyright headers (Checkmk GmbH, GPLv2). Applied only in Stage 7 via
  `scripts/apply-checkmk-headers.sh` shortly before the first merge.
- `BUILD.bazel` content — written when Bazel is introduced (Stage 2/6).
- `LICENSE` — the upstream file is pulled in at merge time.

## How the built-in delivery relates to the external MKP

OrbVis ships on two tracks after Stage 6 is complete:

- **built-in** (CMK 2.6+): code lives here, will be merged into the Checkmk
  source tree, owned by Checkmk GmbH under GPLv2.
- **external MKP / standalone** (CMK 2.3 / 2.4 / 2.5): code continues to live
  under `backend/`, `frontend/`, `cmk_plugins/`, `cmk_plugins_23/` at the
  repo root, pulled into MKP archives the existing way.

The two tracks coexist; they are not alternatives. Bug fixes are cherry-picked
between them where applicable.

## Open questions (to clarify before Stage 6 starts)

1. Tailwind in the built-in bundle? cmk-frontend-vue uses CMK SCSS tokens —
   does legal/design accept Tailwind alongside?
2. Backend URL of the external OrbVis backend: how does the built-in frontend
   discover it? OMD site-setting, env var, configuration UI in `cmk/gui/orbvis/`?
3. Node version for the external `frontend/` tree when the built-in goes to
   Node 22+ — upgrade both or keep the external tree at 18+?
4. CLA / copyright transfer agreement with Checkmk GmbH — signed?
