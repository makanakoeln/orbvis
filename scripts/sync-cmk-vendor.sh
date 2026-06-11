#!/usr/bin/env bash
# Drift-check between frontend/src/vendor/cmk/ and ~/git/checkmk/packages/cmk-frontend-vue/.
#
# Always pulls the checkmk branch first so the diff is against current master
# (or whatever ref is checked out). Intentional patches live in
# scripts/cmk-vendor-patches.txt and are reported separately from real drift.
#
# Exit codes:
#   0  identical or only patched files
#   1  drift detected (file content differs and not on the patch list)
#   2  setup error (paths missing, git unavailable, ...)
#
# Usage:
#   scripts/sync-cmk-vendor.sh                 summary
#   scripts/sync-cmk-vendor.sh --show-diff X   diff a specific vendored path

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/.." && pwd)"
VENDOR_DIR="$REPO_ROOT/frontend/src/vendor/cmk"
CMK_ROOT="${CMK_ROOT:-$HOME/git/checkmk}"
CMK_FRONTEND="$CMK_ROOT/packages/cmk-frontend-vue/src"
PATCH_LIST="$REPO_ROOT/scripts/cmk-vendor-patches.txt"
SHOW_DIFF=""

# Prettier normalises both files to OrbVis style before diffing — kills the
# noise from old vendored 4-space/semicolon style vs the cmk-style config.
PRETTIER_BIN="$REPO_ROOT/frontend/node_modules/.bin/prettier"
PRETTIER_CONFIG="$REPO_ROOT/frontend/prettier.config.cjs"
if [[ ! -x "$PRETTIER_BIN" ]]; then
  echo "prettier binary missing at $PRETTIER_BIN — run npm install in frontend/" >&2
  exit 2
fi
if [[ ! -f "$PRETTIER_CONFIG" ]]; then
  # normalize() falls back to raw content on prettier failure; a missing
  # config would silently disable normalisation for EVERY file and flood
  # the report with pure format drift. Fail loudly instead.
  echo "prettier config missing at $PRETTIER_CONFIG" >&2
  exit 2
fi

normalize() {
  # Pipe a file through prettier; on parse failure return the raw content so
  # diff still reports something useful instead of erroring out the script.
  local file=$1
  local parser
  case "$file" in
    *.vue) parser=vue ;;
    *.ts)  parser=typescript ;;
    *)     parser=babel ;;
  esac
  "$PRETTIER_BIN" --parser "$parser" --config "$PRETTIER_CONFIG" --no-error-on-unmatched-pattern <"$file" 2>/dev/null \
    || cat "$file"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --show-diff)
      SHOW_DIFF="${2:?Usage: --show-diff <path>}"
      shift 2
      ;;
    -h|--help)
      sed -n '2,15p' "${BASH_SOURCE[0]}"
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      exit 2
      ;;
  esac
done

if [[ ! -d "$CMK_ROOT/.git" ]]; then
  echo "checkmk repo not found at $CMK_ROOT" >&2
  echo "Set CMK_ROOT=/path/to/checkmk if your clone lives elsewhere." >&2
  exit 2
fi

if [[ ! -d "$CMK_FRONTEND" ]]; then
  echo "cmk-frontend-vue/src not found at $CMK_FRONTEND" >&2
  exit 2
fi

echo "→ git pull in $CMK_ROOT (branch: $(cd "$CMK_ROOT" && git rev-parse --abbrev-ref HEAD))"
(cd "$CMK_ROOT" && git pull --ff-only --quiet) || {
  echo "git pull failed — resolve conflicts in $CMK_ROOT before rerunning." >&2
  exit 2
}
echo "  → HEAD now at $(cd "$CMK_ROOT" && git rev-parse --short HEAD)"
echo

# Load patch manifest into an associative array (path → rationale).
declare -A PATCHED=()
if [[ -f "$PATCH_LIST" ]]; then
  while IFS= read -r line; do
    [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue
    # First whitespace-run separates path from rationale.
    path="${line%%[[:space:]]*}"
    rationale="${line#"$path"}"
    rationale="${rationale#"${rationale%%[![:space:]]*}"}"
    PATCHED["$path"]="$rationale"
  done < "$PATCH_LIST"
fi

# --show-diff short-circuit: print the diff for one path and exit.
if [[ -n "$SHOW_DIFF" ]]; then
  vendor_file="$VENDOR_DIR/$SHOW_DIFF"
  upstream_file="$CMK_FRONTEND/$SHOW_DIFF"
  if [[ ! -f "$vendor_file" ]]; then
    echo "vendor file not found: $vendor_file" >&2
    exit 2
  fi
  if [[ ! -f "$upstream_file" ]]; then
    echo "upstream file not found: $upstream_file" >&2
    exit 2
  fi
  diff -u --label "upstream/$SHOW_DIFF" --label "vendor/$SHOW_DIFF" \
    <(normalize "$upstream_file") <(normalize "$vendor_file") || true
  exit 0
fi

identical=0
patched=0
drift=0
upstream_missing=0
drift_paths=()
patched_paths=()
missing_paths=()

# Walk every vendored .vue / .ts file and compare to its upstream sibling.
while IFS= read -r -d '' vendor_file; do
  rel="${vendor_file#"$VENDOR_DIR/"}"
  upstream_file="$CMK_FRONTEND/$rel"
  if [[ ! -f "$upstream_file" && "$rel" == tests/* ]]; then
    # Vendored upstream test suites mirror cmk-frontend-vue/tests/ (a sibling
    # of src/) so the fixtures pin byte-identical formatter behaviour.
    upstream_file="$CMK_FRONTEND/../$rel"
  fi
  if [[ ! -f "$upstream_file" ]]; then
    upstream_missing=$((upstream_missing + 1))
    missing_paths+=("$rel")
    continue
  fi
  # Compare after running both sides through prettier — eliminates the
  # semicolon/indent noise so only real code drift surfaces.
  if diff -q <(normalize "$upstream_file") <(normalize "$vendor_file") >/dev/null 2>&1; then
    identical=$((identical + 1))
    continue
  fi
  if [[ -n "${PATCHED[$rel]:-}" ]]; then
    patched=$((patched + 1))
    patched_paths+=("$rel")
    continue
  fi
  drift=$((drift + 1))
  drift_paths+=("$rel")
done < <(find "$VENDOR_DIR" -type f \( -name '*.vue' -o -name '*.ts' \) -print0)

total=$((identical + patched + drift + upstream_missing))

printf "Vendor sync report\n"
printf "  Vendor root:   %s\n" "$VENDOR_DIR"
printf "  Upstream root: %s\n" "$CMK_FRONTEND"
printf "  Files checked: %d\n\n" "$total"

printf "  ✓ identical:           %d\n" "$identical"
printf "  ◆ patched (manifest):  %d\n" "$patched"
printf "  ✗ drift:               %d\n" "$drift"
printf "  ? upstream missing:    %d\n\n" "$upstream_missing"

if (( patched > 0 )); then
  printf "Patched files (intentional):\n"
  for p in "${patched_paths[@]}"; do
    printf "  ◆ %s\n      %s\n" "$p" "${PATCHED[$p]}"
  done
  printf "\n"
fi

if (( drift > 0 )); then
  printf "Drift detected — upstream changed without manifest entry:\n"
  for p in "${drift_paths[@]}"; do
    printf "  ✗ %s\n" "$p"
  done
  printf "\n  Inspect with: scripts/sync-cmk-vendor.sh --show-diff <path>\n"
fi

if (( upstream_missing > 0 )); then
  printf "Vendor-only files (no upstream counterpart):\n"
  for p in "${missing_paths[@]}"; do
    printf "  ? %s\n" "$p"
  done
  printf "\n"
fi

exit $(( drift > 0 ? 1 : 0 ))
