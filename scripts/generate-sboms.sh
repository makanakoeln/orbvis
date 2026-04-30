#!/bin/bash
# generate-sboms.sh — produce CycloneDX SBOMs for backend and frontend.
#
# Output:
#   sbom-backend.cdx.json
#   sbom-frontend.cdx.json
#
# Run from the repo root.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$SCRIPT_DIR")"
OUT_DIR="${1:-$ROOT}"

mkdir -p "$OUT_DIR"

echo "▸ Backend SBOM"
if ! command -v cyclonedx-py >/dev/null 2>&1; then
  pip install --quiet cyclonedx-bom
fi
( cd "$ROOT/backend" && cyclonedx-py environment \
  --output-file "$OUT_DIR/sbom-backend.cdx.json" \
  --output-format json )
echo "  → $OUT_DIR/sbom-backend.cdx.json"

echo "▸ Frontend SBOM"
( cd "$ROOT/frontend" && npm sbom --sbom-format=cyclonedx > "$OUT_DIR/sbom-frontend.cdx.json" )
echo "  → $OUT_DIR/sbom-frontend.cdx.json"

echo ""
echo "Done. Attach both files to the GitHub release."
