#!/usr/bin/env bash
# Generate upstream-checkmk/packages/cmk-orbvis-backend/cmk/orbvis_backend
# from backend/app.
#
# The built-in Checkmk variant ships the FastAPI backend as a site-local
# daemon (agent-receiver model: skel/init.d + CONFIG_ORBVIS hook). This script
# is the single source of truth for the mechanical transform between the
# standalone backend and the in-tree package:
#
#   1. rsync backend/app -> package cmk/orbvis_backend, dropping bytecode.
#   2. Remap absolute imports 'from app.' -> 'from cmk.orbvis_backend.'
#      (relative '.'/'..' imports are unaffected by the package move).
#   3. Disambiguate the geo-tile module (api/v1/maps.py), which already owns
#      the name "maps", BEFORE the board->map rename would collide with it.
#   4. Rename the OrbVis "board" domain term to "map" (see the codemod).
#   5. Prepend the Checkmk GPLv2 header to every module that lacks it.
#
# The standalone-only paths (SQLite/JWT auth, version-compat bridges) are kept
# for now and gated at runtime via settings.checkmk_omd_root -- exactly like
# the frontend package still ships its *Legacy.vue components. Stripping them
# is a deliberate later cleanup (D1), not part of this mechanical sync.
#
# Usage:
#   scripts/sync-upstream-backend.sh [--check]
#
#   --check   dry-run: report drift against the committed package, exit 1 on
#             drift. Used by CI / pre-merge ritual.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="$REPO_ROOT/backend/app"
DEST="${ORBVIS_UPSTREAM_BACKEND_DEST:-$REPO_ROOT/upstream-checkmk/packages/cmk-orbvis-backend}"
PKG_REL="cmk/orbvis_backend"

CHECK=0
[[ "${1:-}" == "--check" ]] && CHECK=1

err() { printf 'ERROR: %s\n' "$*" >&2; }
note() { printf '[sync-backend] %s\n' "$*"; }

[[ -d "$SRC" ]] || { err "missing $SRC"; exit 2; }

stage="$(mktemp -d -t orbvis-backend-sync.XXXXXX)"
trap 'rm -rf "$stage"' EXIT
pkg="$stage/$PKG_REL"

# --- 1. copy the app tree --------------------------------------------------
mkdir -p "$pkg"
rsync -a --exclude='__pycache__/' --exclude='*.pyc' "$SRC/" "$pkg/"

# --- 2. absolute import remap: app -> cmk.orbvis_backend -------------------
# Only absolute 'from app.' / 'from app import' imports move; the FastAPI
# instance attribute access (app.get/app.mount/...) and relative imports stay.
while IFS= read -r -d '' f; do
    sed -i \
        -e 's/\bfrom app\./from cmk.orbvis_backend./g' \
        -e 's/\bfrom app import\b/from cmk.orbvis_backend import/g' \
        "$f"
done < <(find "$pkg" -type f -name '*.py' -print0)

# --- 3. disambiguate the geo-tile module -----------------------------------
# api/v1/maps.py is the OpenStreetMap tile cache proxy -- it already owns the
# name "maps". Rename it to map_tiles so the board->map rename below can turn
# the boards CRUD router into the "maps" resource without clobbering it. The
# module is referenced only from main.py (import tuple + maps.router). The
# route prefix string "/api/v1/maps" is left untouched.
mv "$pkg/api/v1/maps.py" "$pkg/api/v1/map_tiles.py"
sed -i \
    -e 's/^\( *\)maps,$/\1map_tiles,/' \
    -e 's/\bmaps\.router\b/map_tiles.router/g' \
    "$pkg/main.py"

# --- 4. board -> map domain rename -----------------------------------------
note "applying board->map rename"
python3 "$REPO_ROOT/scripts/rename-board-to-map.py" "$pkg"

# --- 5. Checkmk GPLv2 header ------------------------------------------------
python3 - "$pkg" <<'PY'
import sys
from pathlib import Path

HEADER = (
    "#!/usr/bin/env python3\n"
    "# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2\n"
    "# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and\n"
    "# conditions defined in the file COPYING, which is part of this source code package.\n"
)
COPYRIGHT = (
    "# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2\n"
    "# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and\n"
    "# conditions defined in the file COPYING, which is part of this source code package.\n"
)

for p in Path(sys.argv[1]).rglob("*.py"):
    text = p.read_text(encoding="utf-8")
    head = "".join(text.splitlines(keepends=True)[:5])
    if "Copyright (C)" in head:
        continue
    if text.startswith("#!"):
        first, rest = text.split("\n", 1)
        p.write_text(first + "\n" + COPYRIGHT + rest, encoding="utf-8")
    else:
        p.write_text(HEADER + text, encoding="utf-8")
PY

# --- 6. install or diff -----------------------------------------------------
if [[ "$CHECK" -eq 1 ]]; then
    if diff -r -q "$pkg" "$DEST/$PKG_REL" >/dev/null 2>&1; then
        note "package is in sync"
        exit 0
    fi
    err "drift in $PKG_REL (run scripts/sync-upstream-backend.sh)"
    diff -r -q "$pkg" "$DEST/$PKG_REL" 2>&1 | head -30 >&2 || true
    exit 1
fi

mkdir -p "$DEST/$PKG_REL"
rsync -a --delete "$pkg/" "$DEST/$PKG_REL/"
note "synced into $DEST/$PKG_REL"
