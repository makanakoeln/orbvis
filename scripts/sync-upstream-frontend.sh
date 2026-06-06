#!/usr/bin/env bash
# Sync frontend/src into upstream-checkmk/packages/cmk-orbvis-frontend/src.
#
# The upstream package is the built-in Checkmk variant of the OrbVis
# frontend: it compiles against the REAL cmk-frontend-vue sources
# (sibling package in the checkmk monorepo) instead of the vendored
# copy under frontend/src/vendor/cmk. This script is the single source
# of truth for the mechanical transformation between the two worlds:
#
#   1. rsync frontend/src -> package src, dropping everything that only
#      exists to make the external repo self-contained (vendor tree,
#      standalone component overrides, stubs, generated catalogs).
#   2. Re-home the OrbVis-OWNED vendor files (custom FormSpec widgets,
#      patched dispatcher, upstream-orphans) under src/cmk-additions/.
#   3. Rewrite imports: '@/vendor/cmk/...' -> '@cmk/...' plus explicit
#      renames where upstream master reorganized files, plus redirects
#      for the owned files.
#   4. Verify every '@cmk/...' import resolves against the real
#      cmk-frontend-vue source tree -- upstream refactors surface here
#      as a hard error instead of a broken monorepo build.
#
# Usage:
#   scripts/sync-upstream-frontend.sh [--check]
#
#   --check   dry-run: report what would change (drift check), exit 1 on
#             drift. Used by CI / pre-merge ritual.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="$REPO_ROOT/frontend"
DEST="$REPO_ROOT/upstream-checkmk/packages/cmk-orbvis-frontend"
CMK_SRC="${CMK_FRONTEND_VUE_SRC:-$HOME/git/checkmk/packages/cmk-frontend-vue/src}"

CHECK=0
[[ "${1:-}" == "--check" ]] && CHECK=1

err() { printf 'ERROR: %s\n' "$*" >&2; }
note() { printf '[sync-upstream] %s\n' "$*"; }

[[ -d "$SRC/src" ]] || { err "missing $SRC/src"; exit 2; }
[[ -d "$CMK_SRC" ]] || { err "missing cmk-frontend-vue source at $CMK_SRC (set CMK_FRONTEND_VUE_SRC)"; exit 2; }

# --- OrbVis-owned vendor files -------------------------------------------
# Files that live inside frontend/src/vendor/cmk but have no (current)
# upstream counterpart. They move to src/cmk-additions/<same-rel-path>.
#  - FormOrb*.vue + dispatch.ts: OrbVis custom FormSpec widgets + the
#    dispatcher patch that registers them (see cmk-vendor-patches.txt).
#  - CmkDialog.vue, lib/rest-api-client/userConfig.ts: upstream removed
#    these after we vendored them; OrbVis still depends on them.
OWNED_FILES=(
    components/CmkDialog.vue
    lib/rest-api-client/userConfig.ts
    form/private/forms/FormOrbColor.vue
    form/private/forms/FormOrbHostAutocomplete.vue
    form/private/FormEditDispatcher/dispatch.ts
)

# Import rewrites applied to the whole copied tree, most-specific first.
# Left side matches the import string as it appears in frontend/src
# (after the generic vendor->@cmk rewrite); right side is the monorepo
# form. Renames exist because upstream master reorganized flat files
# into directories (or vice versa) after we vendored them.
declare -A IMPORT_RENAMES=(
    # upstream turned the flat file into a directory with index.ts
    ["@cmk/components/CmkButton.vue"]="@cmk/components/CmkButton"
    # upstream flattened the directory back into a single .vue file
    ["@cmk/components/CmkCode/CmkCode.vue"]="@cmk/components/CmkCode.vue"
    ["@cmk/components/CmkChip/CmkChip.vue"]="@cmk/components/CmkChip.vue"
    # OrbVis-owned files re-homed under cmk-additions
    ["@cmk/components/CmkDialog.vue"]="@/cmk-additions/components/CmkDialog.vue"
    ["@cmk/lib/rest-api-client/userConfig"]="@/cmk-additions/lib/rest-api-client/userConfig"
    ["@cmk/form/private/forms/FormOrbColor.vue"]="@/cmk-additions/form/private/forms/FormOrbColor.vue"
    ["@cmk/form/private/forms/FormOrbHostAutocomplete.vue"]="@/cmk-additions/form/private/forms/FormOrbHostAutocomplete.vue"
    ["@cmk/form/private/FormEditDispatcher/dispatch"]="@/cmk-additions/form/private/FormEditDispatcher/dispatch"
)

stage="$(mktemp -d -t orbvis-upstream-sync.XXXXXX)"
trap 'rm -rf "$stage"' EXIT

# --- 1. copy the app tree --------------------------------------------------
# cmk-stubs is mostly build-stubs for unbundleable vendor deps (real
# modules exist in the monorepo), EXCEPT the two genuine OrbVis form
# overrides registered via orbFormComponents.ts — those ship.
rsync -a \
    --exclude='vendor/' \
    --exclude='components/cmk-standalone/' \
    --exclude='components/cmk-stubs/' \
    --include='/cmk-stubs/' \
    --include='/cmk-stubs/FormBooleanChoice.vue' \
    --include='/cmk-stubs/FormMultilineText.vue' \
    --exclude='/cmk-stubs/**' \
    "$SRC/src/" "$stage/src/"

# Top-level package inputs that are part of the app, not of the toolchain
# (configs like vite.config.ts/tsconfig are authored in the upstream
# package and NOT synced).
mkdir -p "$stage/public" "$stage/locale"
cp "$SRC/index.html" "$stage/index.html"
rsync -a "$SRC/public/" "$stage/public/"
cp "$SRC/locale/de.po" "$stage/locale/de.po"

# --- 2. re-home owned vendor files ----------------------------------------
for rel in "${OWNED_FILES[@]}"; do
    src_file="$SRC/src/vendor/cmk/$rel"
    [[ -f "$src_file" ]] || { err "owned vendor file missing: $rel"; exit 2; }
    mkdir -p "$stage/src/cmk-additions/$(dirname "$rel")"
    cp "$src_file" "$stage/src/cmk-additions/$rel"
done

# --- 3a. generic rewrite: vendor imports -> @cmk ---------------------------
# (find -print0 keeps us safe against exotic file names)
while IFS= read -r -d '' f; do
    sed -i "s|'@/vendor/cmk/|'@cmk/|g" "$f"
done < <(find "$stage/src" -type f \( -name '*.ts' -o -name '*.vue' \) -print0)

# --- 3b. owned-file internal imports ---------------------------------------
# Inside cmk-additions the vendored files used upstream's '@/...' style
# (meaning "cmk-frontend-vue src"). Re-point each import to '@cmk/...'
# IFF the target exists in the real CMK tree, otherwise keep '@/...'
# (it is an OrbVis app module the widget intentionally reaches into).
# This freezes, at sync time, the OrbVis-shadows-CMK resolution that the
# external repo performs at build time.
resolve_in() {
    # resolve_in <base-dir> <import-path-without-alias> -> 0 if it resolves
    local base="$1" p="$2"
    local cand
    for cand in "" ".ts" ".vue" "/index.ts" "/index.vue"; do
        [[ -f "$base/$p$cand" ]] && return 0
    done
    return 1
}

while IFS= read -r -d '' f; do
    # collect this file's '@/...' imports and decide per import:
    # CMK module -> '@cmk/...', fellow owned file -> '@/cmk-additions/...',
    # anything else is an OrbVis app module and stays '@/...'.
    while IFS= read -r imp; do
        rel="${imp#@/}"
        if resolve_in "$CMK_SRC" "$rel"; then
            sed -i "s|'$imp'|'@cmk/$rel'|g" "$f"
        elif resolve_in "$stage/src/cmk-additions" "$rel"; then
            sed -i "s|'$imp'|'@/cmk-additions/$rel'|g" "$f"
        fi
    done < <(grep -hoE "'@/[^']+'" "$f" | tr -d "'" | sort -u)
    # relative imports: resolve against the file's original vendor
    # location so './constants' & friends keep pointing into CMK
    rel_dir="$(dirname "${f#"$stage"/src/cmk-additions/}")"
    while IFS= read -r imp; do
        # realpath -m normalizes ../ segments; the /__virtual__ prefix
        # keeps it away from real filesystem entries (a bare /lib/...
        # would follow the host's /lib -> /usr/lib symlink).
        abs="$(realpath -m "/__virtual__/$rel_dir/$imp")"
        abs="${abs#/__virtual__/}"
        if resolve_in "$stage/src/cmk-additions" "$abs"; then
            sed -i "s|'$imp'|'@/cmk-additions/$abs'|g" "$f"
        elif resolve_in "$CMK_SRC" "$abs"; then
            sed -i "s|'$imp'|'@cmk/$abs'|g" "$f"
        fi
    done < <(grep -hoE "'\.\.?/[^']+'" "$f" | tr -d "'" | sort -u)
done < <(find "$stage/src/cmk-additions" -type f \( -name '*.ts' -o -name '*.vue' \) -print0)

# --- 3c. explicit renames (most-specific, after the generic pass) ----------
while IFS= read -r -d '' f; do
    for from in "${!IMPORT_RENAMES[@]}"; do
        sed -i "s|'$from'|'${IMPORT_RENAMES[$from]}'|g" "$f"
    done
done < <(find "$stage/src" -type f \( -name '*.ts' -o -name '*.vue' \) -print0)

# --- 3d. API-drift fixups ---------------------------------------------------
# File-specific rewrites bridging drift between the vendored CMK copy
# and current master. Each MUST apply — a silent no-op means the source
# moved or the drift resolved (drop the rule then). All disappear with
# the next full vendor refresh.
apply_fixup() {
    # apply_fixup <file-rel-to-stage> <sed-expr> <must-match-after>
    local rel="$1" expr="$2" expect="$3"
    [[ -f "$stage/$rel" ]] || { err "fixup target missing: $rel"; exit 1; }
    sed -i "$expr" "$stage/$rel"
    grep -qF "$expect" "$stage/$rel" \
        || { err "fixup did not apply in $rel (expected: $expect)"; exit 1; }
}

# Upstream renamed CmkCode's prop codeTxt -> codeText after we vendored
# it. The vendored copy keeps the old name (external world), master
# expects the new one (monorepo world).
apply_fixup "src/components/board/DetailDrawer.vue" \
    's|:code-txt=|:code-text=|g' \
    ':code-text='

# vue-language-tools resolves directory imports from .vue importers to a
# same-named SFC inside the directory (CmkButton/CmkButton.vue) — fine
# for the default export, but named TYPE re-exports through index.ts
# become invisible. Import the type straight from its defining module.
apply_fixup "src/cmk-additions/components/CmkDialog.vue" \
    "s|import type { ButtonVariants } from '@cmk/components/CmkButton'|import type { ButtonVariants } from '@cmk/components/CmkButton/types'|" \
    "@cmk/components/CmkButton/types"

# --- 4. verify every @cmk import resolves ----------------------------------
fail=0
while IFS= read -r -d '' f; do
    while IFS= read -r imp; do
        rel="${imp#@cmk/}"
        if ! resolve_in "$CMK_SRC" "$rel"; then
            err "unresolved @cmk import '$imp' in ${f#"$stage"/}"
            fail=1
        fi
    done < <(grep -hoE "'@cmk/[^']+'" "$f" | tr -d "'" | sort -u)
done < <(find "$stage/src" -type f \( -name '*.ts' -o -name '*.vue' \) -print0)

if grep -rn "@/vendor" "$stage/src" --include='*.ts' --include='*.vue' >/dev/null; then
    err "leftover '@/vendor' references:"
    grep -rn "@/vendor" "$stage/src" --include='*.ts' --include='*.vue' >&2
    fail=1
fi
[[ "$fail" -eq 0 ]] || { err "verification failed -- upstream cmk-frontend-vue moved files? Update IMPORT_RENAMES/OWNED_FILES."; exit 1; }
note "all @cmk imports resolve against $CMK_SRC"

# --- 5. install or diff -----------------------------------------------------
SYNCED=(src index.html public locale/de.po)
if [[ "$CHECK" -eq 1 ]]; then
    drift=0
    for p in "${SYNCED[@]}"; do
        if ! diff -r -q "$stage/$p" "$DEST/$p" >/dev/null 2>&1; then
            err "drift in $p (run scripts/sync-upstream-frontend.sh)"
            diff -r -q "$stage/$p" "$DEST/$p" 2>&1 | head -20 >&2 || true
            drift=1
        fi
    done
    [[ "$drift" -eq 0 ]] && note "package is in sync"
    exit "$drift"
fi

mkdir -p "$DEST/locale"
rsync -a --delete "$stage/src/" "$DEST/src/"
rsync -a --delete "$stage/public/" "$DEST/public/"
cp "$stage/index.html" "$DEST/index.html"
cp "$stage/locale/de.po" "$DEST/locale/de.po"
note "synced into $DEST"
