#!/bin/bash
# make_mkp.sh – Build OrbVis as a Checkmk MKP package
#
# Usage:
#   ./make_mkp.sh [--version 1.2.3] [--cmk-target 2.3|2.4|2.5|2.6] [--out /path/to/output]
#
# --cmk-target selects the CMK GUI-plugin set bundled in the MKP:
#   2.3  – cmk_plugins_23/ (flat layout, CMK 2.3); default
#   2.4  – cmk_plugins_23/ (flat layout, CMK 2.4)
#   2.5  – cmk_plugins/    (namespace-package layout for CMK 2.5+)
#   2.6  – cmk_plugins/    (namespace-package layout for CMK 2.6)
#
# The default version is read from the VERSION file in the repo root; pass
# --version to override.
#
# Creates a self-contained .mkp that can be installed via:
#   mkp add orbvis-<version>-cmk-<target>.mkp && mkp enable orbvis
#
# After MKP installation, run once as the site user:
#   su - <SITE> -c "orbvis-setup"
#
set -euo pipefail

BOLD='\033[1m'; GREEN='\033[0;32m'; YELLOW='\033[0;33m'; RED='\033[0;31m'; RESET='\033[0m'
step()  { echo -e "  ${BOLD}▸ $*${RESET}"; }
ok()    { echo -e "  ${GREEN}✓ $*${RESET}"; }
warn()  { echo -e "  ${YELLOW}⚠ $*${RESET}"; }
die()   { echo -e "\n${RED}Error: $*${RESET}\n" >&2; exit 1; }

# ---------------------------------------------------------------------------
# Arguments
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Default version comes from the VERSION file (single source of truth).
if [[ -f "$SCRIPT_DIR/VERSION" ]]; then
  VERSION="$(tr -d '[:space:]' < "$SCRIPT_DIR/VERSION")"
else
  VERSION="0.0.0"
fi
CMK_TARGET="2.3"
OUT_DIR="$(pwd)"
SKIP_FRONTEND=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --version)        VERSION="$2";    shift 2 ;;
    --cmk-target)     CMK_TARGET="$2"; shift 2 ;;
    --out)            OUT_DIR="$2";    shift 2 ;;
    --skip-frontend)  SKIP_FRONTEND=1; shift ;;
    *) die "Unknown argument: $1" ;;
  esac
done

case "$CMK_TARGET" in
  2.3) MIN_REQUIRED="2.3.0"; PACKAGED="2.3.0p1";  PLUGIN_SRC="$SCRIPT_DIR/cmk_plugins_23" ;;
  2.4) MIN_REQUIRED="2.4.0"; PACKAGED="2.4.0p1";  PLUGIN_SRC="$SCRIPT_DIR/cmk_plugins_23" ;;
  2.5) MIN_REQUIRED="2.5.0"; PACKAGED="2.5.0p1";  PLUGIN_SRC="$SCRIPT_DIR/cmk_plugins" ;;
  2.6) MIN_REQUIRED="2.6.0"; PACKAGED="2.6.0b1";  PLUGIN_SRC="$SCRIPT_DIR/cmk_plugins" ;;
  *) die "Unsupported --cmk-target: $CMK_TARGET (allowed: 2.3, 2.4, 2.5, 2.6)" ;;
esac

[[ -d "$PLUGIN_SRC" ]] || die "Plugin source directory not found: $PLUGIN_SRC"

# Filename intentionally omits the version — Checkmk Exchange keeps the upload
# filename constant across versions so users have a stable download URL. The
# release version lives inside the MKP manifest (info / info.json).
MKP_NAME="orbvis-cmk-${CMK_TARGET}.mkp"
MKP_OUT="${OUT_DIR}/${MKP_NAME}"
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

echo ""
echo -e "${BOLD}Building OrbVis MKP v${VERSION} (CMK target ${CMK_TARGET})${RESET}"
echo ""

# ---------------------------------------------------------------------------
# 1. Build frontend (relative base path → works at any /<SITE>/orbvis/ URL)
#    --skip-frontend lets CI build once and reuse frontend/dist/ across the
#    three cmk-target builds — saves ~3× npm install + vite build.
# ---------------------------------------------------------------------------
if [[ "$SKIP_FRONTEND" == "1" ]]; then
  [[ -d "$SCRIPT_DIR/frontend/dist" ]] \
    || die "--skip-frontend was set but frontend/dist/ is missing. Build it first."
  ok "Frontend reused (skip requested)"
else
  step "Building frontend (relative base path)"
  NPM="$(command -v npm 2>/dev/null || true)"
  [[ -z "$NPM" ]] && die "npm not found. Install Node.js (^20.19 || >=22.12)."
  NODE="$(command -v node 2>/dev/null || true)"
  [[ -z "$NODE" ]] && die "node not found. Install Node.js (^20.19 || >=22.12)."

  # Vite 8 requires Node ^20.19.0 || >=22.12.0 — older versions fail with
  # "node:fs/promises does not provide an export named 'constants'".
  NODE_VERSION="$("$NODE" --version | sed 's/^v//')"
  NODE_OK="$("$NODE" -e '
    const [maj, min] = process.versions.node.split(".").map(Number);
    const ok = (maj === 20 && min >= 19) || (maj === 22 && min >= 12) || maj > 22;
    process.stdout.write(ok ? "1" : "0");
  ')"
  [[ "$NODE_OK" == "1" ]] || die "Node.js $NODE_VERSION is too old.
    Vite 8 requires ^20.19.0 || >=22.12.0.
    Install a newer Node (e.g. via nvm: 'nvm install 22 && nvm use 22')."
  cd "$SCRIPT_DIR/frontend"
  npm install --silent
  VITE_BASE_PATH=./ npm run build -- --base='./' --logLevel=warn 2>&1 | awk '
    /didn.t resolve at build time, it will remain unchanged to be resolved at runtime/ { next }
    /^\[plugin builtin:vite-reporter\]/ { next }
    /^\(!\) Some chunks are larger than/ { next }
    /^- Using dynamic import\(\) to code-split/ { next }
    /^- Use build\.rolldownOptions/ { next }
    /^- Adjust chunk size limit/ { next }
    { is_blank = ($0 ~ /^[[:space:]]*$/); if (is_blank && prev_blank) next; prev_blank = is_blank; print }
  '
  ok "Frontend built"
fi

# ---------------------------------------------------------------------------
# 2. Stage directory structure for MKP
# ---------------------------------------------------------------------------
step "Staging MKP structure"
mkdir -p "$TMPDIR/lib/orbvis"

# GUI plugins: layout differs by plugin source (flat for 2.3/2.4, namespace for 2.5+).
if [[ "$PLUGIN_SRC" == "$SCRIPT_DIR/cmk_plugins_23" ]]; then
  # Flat layout under local/share/check_mk/web/plugins/
  mkdir -p "$TMPDIR/web/plugins/sidebar" "$TMPDIR/web/plugins/wato"
  cp "$PLUGIN_SRC/orbvis_sidebar.py"     "$TMPDIR/web/plugins/sidebar/orbvis_sidebar.py"
  cp "$PLUGIN_SRC/orbvis_menu.py"        "$TMPDIR/web/plugins/wato/orbvis_menu.py"
  cp "$PLUGIN_SRC/orbvis_permissions.py" "$TMPDIR/web/plugins/wato/orbvis_permissions.py"
else
  # CMK 2.5+ namespace-package layout under local/lib/python3/cmk/gui/plugins/
  mkdir -p "$TMPDIR/lib/python3/cmk/gui/plugins/sidebar" \
           "$TMPDIR/lib/python3/cmk/gui/plugins/wato"
  cp "$PLUGIN_SRC/cmk/gui/plugins/sidebar/orbvis_boards.py" \
     "$TMPDIR/lib/python3/cmk/gui/plugins/sidebar/orbvis_boards.py"
  cp "$PLUGIN_SRC/cmk/gui/plugins/wato/orbvis_menu.py" \
     "$TMPDIR/lib/python3/cmk/gui/plugins/wato/orbvis_menu.py"
  cp "$PLUGIN_SRC/cmk/gui/plugins/wato/orbvis_permissions.py" \
     "$TMPDIR/lib/python3/cmk/gui/plugins/wato/orbvis_permissions.py"
fi

# Frontend: single tarball → lib/orbvis/htdocs.tar.gz
# orbvis-setup extracts it to $OMD_ROOT/var/orbvis/htdocs/
tar czf "$TMPDIR/lib/orbvis/htdocs.tar.gz" -C "$SCRIPT_DIR/frontend/dist" .

# Backend: single tarball → lib/orbvis/server.tar.gz
# Excludes drop the dev virtualenv, build caches and on-disk databases — they
# would otherwise add ~80 MB of dev clutter to the .mkp.
tar czf "$TMPDIR/lib/orbvis/server.tar.gz" \
  --exclude=".venv" \
  --exclude="__pycache__" \
  --exclude="*.pyc" \
  --exclude=".pytest_cache" \
  --exclude=".mypy_cache" \
  --exclude=".ruff_cache" \
  --exclude="*.db" \
  --exclude="*.db-journal" \
  --exclude="backends.json" \
  --exclude="connections.json" \
  --exclude="boards" \
  --exclude="images" \
  -C "$SCRIPT_DIR/backend" .

# Wheelhouse: orbvis_backend wheel + python-multipart (only runtime dep OMD
# lacks at our CVE floor). pip download silently skips wheels it cannot find
# for the target python/platform; the offline install then fails loudly with
# a missing dep, which is the desired behaviour.
step "Building wheelhouse"
case "$CMK_TARGET" in
  2.3) WHEELHOUSE_PYVER=3.12; BUNDLE_FILE=requirements-bundle-cmk23.txt ;;
  2.4) WHEELHOUSE_PYVER=3.12; BUNDLE_FILE=requirements-bundle.txt ;;
  2.5|2.6) WHEELHOUSE_PYVER=3.13; BUNDLE_FILE=requirements-bundle.txt ;;
esac
mkdir -p "$TMPDIR/lib/orbvis/wheels"
python3 -m pip wheel --no-deps --wheel-dir "$TMPDIR/lib/orbvis/wheels" "$SCRIPT_DIR/backend" \
  > /dev/null
python3 -m pip download \
  --dest "$TMPDIR/lib/orbvis/wheels" \
  --python-version "$WHEELHOUSE_PYVER" \
  --only-binary=:all: \
  --platform manylinux2014_x86_64 \
  --platform manylinux_2_17_x86_64 \
  --platform manylinux_2_28_x86_64 \
  -r "$SCRIPT_DIR/backend/$BUNDLE_FILE" > /dev/null
ok "Wheelhouse: $(find "$TMPDIR/lib/orbvis/wheels" -maxdepth 1 -type f | wc -l) wheels ($(du -sh "$TMPDIR/lib/orbvis/wheels" | cut -f1))"

# Fallback copy; the backend reads the changelog from its own source tree.
cp "$SCRIPT_DIR/CHANGELOG.md" "$TMPDIR/lib/orbvis/CHANGELOG.md"
# Write $VERSION (which may have been bumped via --version) rather than
# copying $SCRIPT_DIR/VERSION verbatim — otherwise the bundled VERSION file
# never matches the MKP metadata, which breaks the init.d/orbvis auto_refresh
# trigger (it compares this file against $ORBVIS_DIR/.installed-version).
printf '%s\n' "$VERSION" > "$TMPDIR/lib/orbvis/VERSION"

# Demo boards ship inside the wheel; backend seeds them on first start.

ok "Files staged (frontend + backend bundled as tarballs)"

# ---------------------------------------------------------------------------
# 3. Generate orbvis-setup script
# ---------------------------------------------------------------------------
step "Generating orbvis-setup"
mkdir -p "$TMPDIR/bin"
cat > "$TMPDIR/bin/orbvis-setup" << 'SETUP_SCRIPT'
#!/bin/bash
# orbvis-setup – manage OrbVis installation
#
# Commands (run as the OMD site user):
#   orbvis-setup           – install / upgrade OrbVis
#   orbvis-setup uninstall – remove OrbVis (boards and database are kept)
#
set -euo pipefail

BOLD='\033[1m'; GREEN='\033[0;32m'; YELLOW='\033[0;33m'; RED='\033[0;31m'; RESET='\033[0m'
step()  { echo -e "  ${BOLD}▸ $*${RESET}"; }
ok()    { echo -e "  ${GREEN}✓ $*${RESET}"; }
warn()  { echo -e "  ${YELLOW}⚠ $*${RESET}"; }
die()   { echo -e "\n${RED}Error: $*${RESET}\n" >&2; exit 1; }

SITE="${OMD_SITE:-}"
ROOT="${OMD_ROOT:-}"
[[ -z "$SITE" || -z "$ROOT" ]] && die "Run as the OMD site user (OMD_SITE / OMD_ROOT must be set).\nExample: su - <SITE> -c 'orbvis-setup'"

# Layout: user data + install artefacts under var/orbvis/, admin config in
# etc/orbvis/. Both paths sit outside cmk.gui.watolib.activate_changes
# replication_paths so WATO "Activate Changes" never overwrites them.
# The MKP itself still installs into local/lib/orbvis (CMK's MKP machinery
# decides that); orbvis-setup extracts the bundled tarballs from there into
# var/orbvis/ at install time.
MKP_LIB="$ROOT/local/lib/orbvis"
ORBVIS_DIR="$ROOT/var/orbvis"
ORBVIS_ETC_DIR="$ROOT/etc/orbvis"
LEGACY_DIR="$ROOT/local/share/orbvis"
HTDOCS_DIR="$ORBVIS_DIR/htdocs"
BOARDS_DIR="$ORBVIS_DIR/boards"
ENV_FILE="$ORBVIS_ETC_DIR/.env"
CONNECTIONS_FILE="$ORBVIS_DIR/connections.json"
DB_FILE="$ORBVIS_DIR/orbvis.db"
VENV_DIR="$ORBVIS_DIR/venv"
# Outside local/ so a central's "Activate Changes" can't delete the daemon's
# cwd out from under a remote (matches install_cmk.sh's var/orbvis/src).
SERVER_DIR="$ORBVIS_DIR/src"
APACHE_CONF="$ROOT/etc/apache/conf.d/orbvis.conf"
INIT_SCRIPT="$ROOT/etc/init.d/orbvis"
LIVESTATUS_SOCKET="$ROOT/tmp/run/live"

# Pick a TCP port that no other OrbVis install on this host already claims.
# Reuse our own .env if present; otherwise scan all sibling sites' .env files
# (both the new etc/orbvis/.env location and the legacy local/share/ one, so
# a pre-migration install still surfaces its reserved port). Then pick the
# lowest free port from 8420 upward.
discover_port() {
  local existing port envf p
  for probe in "$ENV_FILE" "$LEGACY_DIR/.env"; do
    if [[ -f "$probe" ]]; then
      existing="$(grep -E '^ORBVIS_PORT=' "$probe" | head -1 | cut -d= -f2- || true)"
      if [[ -n "$existing" ]]; then echo "$existing"; return; fi
    fi
  done
  declare -A reserved=()
  for envf in /omd/sites/*/etc/orbvis/.env /omd/sites/*/local/share/orbvis/.env; do
    [[ -f "$envf" && "$envf" != "$ENV_FILE" ]] || continue
    p="$(grep -E '^ORBVIS_PORT=' "$envf" 2>/dev/null | head -1 | cut -d= -f2- || true)"
    [[ -n "$p" ]] && reserved[$p]=1
  done
  port=8420
  while (( port < 8500 )); do
    if [[ -z "${reserved[$port]:-}" ]] \
       && ! ss -tlnH "( sport = :$port )" 2>/dev/null | grep -q .; then
      echo "$port"; return
    fi
    (( port++ ))
  done
  die "No free port available in 8420-8499 for OrbVis backend."
}
BACKEND_PORT="$(discover_port)"

CMD="${1:-setup}"

case "$CMD" in

# ---------------------------------------------------------------------------
uninstall)
# ---------------------------------------------------------------------------
  echo ""
  echo -e "${BOLD}OrbVis Uninstall${RESET}"
  echo "  Site: $SITE  ($ROOT)"
  echo ""

  step "Stopping OrbVis"
  omd stop orbvis 2>/dev/null || true
  ok "OrbVis stopped"

  step "Removing OMD service"
  rm -f "$ROOT/etc/rc.d/85-orbvis"
  rm -f "$INIT_SCRIPT"
  ok "OMD service removed"

  step "Removing Apache configuration"
  rm -f "$APACHE_CONF"
  omd reload apache
  ok "Apache configuration removed"

  step "Removing frontend and backend"
  rm -rf "$HTDOCS_DIR"
  rm -rf "$VENV_DIR"
  rm -rf "$SERVER_DIR"
  rm -rf "$MKP_LIB/server"  # pre-0.4.x extraction location
  # Sweep up any leftovers from pre-migration installs under local/share/orbvis/.
  rm -rf "$LEGACY_DIR/htdocs" "$LEGACY_DIR/venv" "$LEGACY_DIR/cmk_plugins"
  ok "Frontend, venv and backend source removed"

  echo ""
  echo -e "${GREEN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
  echo -e "${GREEN}${BOLD}  OrbVis uninstalled.${RESET}"
  echo -e "${GREEN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
  echo ""
  echo "  Kept (user data):  $BOARDS_DIR"
  echo "                     $DB_FILE"
  echo "                     $ENV_FILE"
  echo "                     $CONNECTIONS_FILE"
  echo ""
  echo "  Remove manually if no longer needed:"
  echo "    rm -rf $ORBVIS_DIR"
  echo ""
  echo -e "  ${YELLOW}${BOLD}Next step: remove the MKP package from Checkmk:${RESET}"
  echo "    mkp disable orbvis"
  echo "    mkp remove orbvis"
  echo ""
  ;;

# ---------------------------------------------------------------------------
setup)
# ---------------------------------------------------------------------------
  [[ -d "$MKP_LIB" ]] || die "MKP library not found at $MKP_LIB\nDid you install the orbvis MKP first?"

  echo ""
  echo -e "${BOLD}OrbVis Post-Install Setup${RESET}"
  echo "  Site: $SITE  ($ROOT)"
  echo ""

  mkdir -p "$ORBVIS_DIR" "$ORBVIS_ETC_DIR"

  # 0. Migrate data from legacy local/share/orbvis/ to var/orbvis/ + etc/orbvis/
  #
  # Up to v0.x OrbVis installed everything under $OMD_ROOT/local/share/orbvis/,
  # which lives inside cmk.gui.watolib.activate_changes.replication_paths
  # (ident="local"). Every WATO Activate Changes pushed boards/db/venv/htdocs
  # to all remote sites. Move user data to var/orbvis/ and the .env to
  # etc/orbvis/ — both paths sit outside the snapshot.
  if [[ -d "$LEGACY_DIR" ]]; then
    step "Migrating data from legacy local/share/orbvis/"
    # ``backends.json`` is the pre-rename predecessor of ``connections.json``;
    # the backend recognises it on startup, so move it along. ``tiles`` is
    # the OSM cache — must move out of local/ to keep it out of the WATO
    # replication snapshot.
    for sub in boards images orbvis.db connections.json backends.json settings.json tiles; do
      if [[ -e "$LEGACY_DIR/$sub" && ! -e "$ORBVIS_DIR/$sub" ]]; then
        mv "$LEGACY_DIR/$sub" "$ORBVIS_DIR/$sub"
      fi
    done
    if [[ -f "$LEGACY_DIR/.env" && ! -f "$ENV_FILE" ]]; then
      mv "$LEGACY_DIR/.env" "$ENV_FILE"
    fi
    # Disposable artefacts; rebuilt below from the MKP-shipped tarballs.
    rm -rf "$LEGACY_DIR/htdocs" "$LEGACY_DIR/venv" \
           "$LEGACY_DIR/cmk_plugins" "$LEGACY_DIR/VERSION" \
           "$LEGACY_DIR/CHANGELOG.md"
    # User-data leftovers that didn't migrate because the destination
    # already existed. Destination is canonical; drop the legacy copy so it
    # can't leak via WATO replication.
    for sub in boards images orbvis.db connections.json backends.json settings.json tiles .env; do
      [[ -e "$LEGACY_DIR/$sub" && -e "$ORBVIS_DIR/$sub" ]] && rm -rf "$LEGACY_DIR/$sub"
    done
    # Drop empty legacy directory so the next replication snapshot has
    # nothing to delete on this site.
    rmdir "$LEGACY_DIR" 2>/dev/null || true
    ok "Migration complete"
  fi

  # 1. Frontend: extract pre-built tarball
  step "Deploying frontend"
  mkdir -p "$HTDOCS_DIR"
  rm -rf "${HTDOCS_DIR:?}"/*
  tar xzf "$MKP_LIB/htdocs.tar.gz" -C "$HTDOCS_DIR"
  ok "Frontend deployed to $HTDOCS_DIR"

  # 2. Backend source: extract tarball
  step "Extracting backend source"
  rm -rf "$MKP_LIB/server"  # pre-0.4.x location, stop it leaking via replication
  rm -rf "${SERVER_DIR:?}"
  mkdir -p "$SERVER_DIR"
  tar xzf "$MKP_LIB/server.tar.gz" -C "$SERVER_DIR"
  # server.tar.gz (built from backend/) lacks these root-level files; the daemon
  # runs from $SERVER_DIR/app, where main.py looks for them first.
  cp "$MKP_LIB/CHANGELOG.md" "$SERVER_DIR/app/CHANGELOG.md"
  cp "$MKP_LIB/VERSION"      "$SERVER_DIR/app/VERSION"
  ok "Backend source extracted"

  # 3. Boards directory — backend seeds bundled demos on first start
  # (gated by a .demo-seeded marker, so user deletions are honored)
  mkdir -p "$BOARDS_DIR/backgrounds"

  # 4. Python virtualenv + backend
  step "Setting up Python environment"

  # Resolve a Python 3.12+ interpreter. Order:
  #   1. PYTHON3 env var (lets users force a specific binary)
  #   2. $OMD_ROOT/bin/python3 (the site Python)
  #   3. python3.13, python3.12 on PATH (deadsnakes / OS package)
  #   4. python3 on PATH (last resort, may be too old)
  py_version_ok() {
    "$1" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)' 2>/dev/null
  }

  PYTHON3="${PYTHON3:-}"
  if [[ -n "$PYTHON3" ]]; then
    [[ -x "$PYTHON3" ]] || die "PYTHON3=$PYTHON3 is not executable."
  else
    for _candidate in \
        "$ROOT/bin/python3" \
        "$(command -v python3.13 2>/dev/null || true)" \
        "$(command -v python3.12 2>/dev/null || true)" \
        "$(command -v python3 2>/dev/null || true)"; do
      [[ -n "$_candidate" && -x "$_candidate" ]] || continue
      if py_version_ok "$_candidate"; then
        PYTHON3="$_candidate"
        break
      fi
    done
  fi

  if [[ -z "$PYTHON3" ]] || ! py_version_ok "$PYTHON3"; then
    FOUND_VERSION="$("${PYTHON3:-python3}" --version 2>&1 || echo 'not found')"
    die "OrbVis requires Python 3.12 or newer.

  Found: $FOUND_VERSION
  Searched: \$PYTHON3, $ROOT/bin/python3, python3.13, python3.12, python3

  Install Python 3.12 and re-run orbvis-setup. On Debian/Ubuntu:
    sudo add-apt-repository ppa:deadsnakes/ppa
    sudo apt install python3.12 python3.12-venv

  Then point orbvis-setup at it explicitly:
    PYTHON3=/usr/bin/python3.12 orbvis-setup"
  fi
  ok "Using $($PYTHON3 --version) ($PYTHON3)"

  # --system-site-packages: 2.6+ ships a sitecustomize.py that imports
  # cmk.licensing on every Python start, which lives in OMD's site-packages.
  # Without the flag the venv shadows that layout and sitecustomize fails.
  # Recreate any pre-existing venv that was built without it.
  if [[ ! -d "$VENV_DIR" ]] || ! grep -q '^include-system-site-packages = true' "$VENV_DIR/pyvenv.cfg" 2>/dev/null; then
    rm -rf "$VENV_DIR"
    "$PYTHON3" -m venv --symlinks --system-site-packages "$VENV_DIR"
  fi
  if [[ ! -L "$VENV_DIR/bin/python3" ]]; then
    ln -sf "$PYTHON3" "$VENV_DIR/bin/python3"
  fi
  step "Installing backend"
  # Offline install: --no-index forbids PyPI, --find-links points at the
  # wheelhouse shipped inside the MKP. Missing deps fall through to the venv's
  # --system-site-packages (the OMD site-python).
  export PIP_DISABLE_PIP_VERSION_CHECK=1
  "$VENV_DIR/bin/pip" install --quiet --no-warn-conflicts \
    --no-index --find-links="$MKP_LIB/wheels" orbvis-backend
  ok "Backend installed"

  # 5. Configuration
  step "Writing configuration"
  EXISTING_SECRET=""
  [[ -f "$ENV_FILE" ]] && EXISTING_SECRET=$(grep -E '^SECRET_KEY=' "$ENV_FILE" | head -1 | cut -d= -f2- || true)
  SECRET_KEY="${EXISTING_SECRET:-$("$PYTHON3" -c 'import secrets; print(secrets.token_hex(32))')}"

  cat > "$ENV_FILE" << EOF
BOARDS_DIR=$BOARDS_DIR
CONNECTIONS_FILE=$CONNECTIONS_FILE
DATABASE_URL=sqlite:///$DB_FILE
SECRET_KEY=$SECRET_KEY
STATE_REFRESH_INTERVAL=15
CHECKMK_HTPASSWD=$ROOT/etc/htpasswd
CHECKMK_OMD_ROOT=$ROOT
CHECKMK_SITE=$SITE
ORBVIS_PORT=$BACKEND_PORT
EOF

  if [[ ! -f "$CONNECTIONS_FILE" ]]; then
    cat > "$CONNECTIONS_FILE" << EOF
[
  {
    "id": "live_1",
    "type": "livestatus",
    "label": "cmk $SITE",
    "socket_path": "$LIVESTATUS_SOCKET",
    "checkmk_url": "/$SITE/check_mk"
  }
]
EOF
    ok "Configuration written"
  else
    ok "Configuration written (existing connections.json kept)"
  fi

  # 6. Apache configuration
  step "Writing Apache configuration"

  PROXY_SO=""
  PROXY_HTTP_SO=""
  for _dir in \
      "$ROOT/lib/apache/modules" \
      "/usr/lib/apache2/modules" \
      "/usr/lib64/httpd/modules" \
      "/usr/lib/httpd/modules"; do
    [[ -z "$PROXY_SO" && -f "$_dir/mod_proxy.so" ]] && PROXY_SO="$_dir/mod_proxy.so"
    [[ -z "$PROXY_HTTP_SO" && -f "$_dir/mod_proxy_http.so" ]] && PROXY_HTTP_SO="$_dir/mod_proxy_http.so"
  done

  if [[ -z "$PROXY_SO" ]]; then
    warn "mod_proxy.so not found — API proxy will be disabled. Backend API will be unreachable."
  fi

  # Only Swagger-UI 5.x renders OpenAPI 3.1 (which FastAPI emits). CMK 2.3/2.4
  # ship swagger-ui-3 only — no Alias there; the backend's /api/docs handler
  # detects that and serves a stub page instead of the broken Swagger shell.
  SWAGGER_UI_DIR=""
  for candidate in "$ROOT"/share/check_mk/web/htdocs/openapi/swagger-ui-5.*; do
    if [[ -f "$candidate/swagger-ui-bundle.js" ]]; then
      SWAGGER_UI_DIR="$candidate"
      break
    fi
  done

  SWAGGER_UI_ALIAS=""
  SWAGGER_UI_PROXYBYPASS=""
  if [[ -n "$SWAGGER_UI_DIR" ]]; then
    SWAGGER_UI_ALIAS="
Alias /$SITE/orbvis/api/swagger-ui $SWAGGER_UI_DIR
<Directory $SWAGGER_UI_DIR>
    Options -Indexes +FollowSymLinks
    AllowOverride None
    Require all granted
</Directory>
"
    SWAGGER_UI_PROXYBYPASS="ProxyPass        /$SITE/orbvis/api/swagger-ui  !"
  fi

  cat > "$APACHE_CONF" << EOF
# OrbVis – static frontend + backend proxy
# Auto-generated by orbvis-setup

<IfModule !mod_proxy.c>
    LoadModule proxy_module $PROXY_SO
</IfModule>
<IfModule !mod_proxy_http.c>
    LoadModule proxy_http_module $PROXY_HTTP_SO
</IfModule>
$SWAGGER_UI_ALIAS
Alias /$SITE/orbvis $HTDOCS_DIR

<Location /$SITE/orbvis>
    AuthType None
    Require all granted
</Location>

<Directory $HTDOCS_DIR>
    Options -Indexes +FollowSymLinks
    AllowOverride None
    Require all granted
    FallbackResource /$SITE/orbvis/index.html
</Directory>

$SWAGGER_UI_PROXYBYPASS
ProxyPass        /$SITE/orbvis/api  http://127.0.0.1:$BACKEND_PORT/api
ProxyPassReverse /$SITE/orbvis/api  http://127.0.0.1:$BACKEND_PORT/api

<Location /$SITE/orbvis/images>
    ProxyPass        http://127.0.0.1:$BACKEND_PORT/images
    ProxyPassReverse http://127.0.0.1:$BACKEND_PORT/images
</Location>

<Location /$SITE/orbvis/boards/backgrounds>
    ProxyPass        http://127.0.0.1:$BACKEND_PORT/boards/backgrounds
    ProxyPassReverse http://127.0.0.1:$BACKEND_PORT/boards/backgrounds
</Location>
EOF
  ok "Apache configuration written"

  # 7. OMD init script
  step "Registering OrbVis as OMD service"
  # auto_refresh (defined in the init script below) runs orbvis-setup from
  # *inside* the still-executing init script during an upgrade restart.
  # Rewriting $INIT_SCRIPT in place would corrupt that running shell: bash
  # reads a script on demand by byte offset, so truncating it mid-run makes it
  # resume parsing garbage (e.g. a stray "xit 1 ;;"). Stage the new script in a
  # sibling temp file and rename() it into place — the running shell keeps its
  # open fd on the old inode while the new content is swapped in atomically.
  INIT_TMP="$(mktemp "$INIT_SCRIPT.XXXXXX")"
  cat > "$INIT_TMP" << EOF
#!/bin/bash
# OMD init script for OrbVis backend

PIDFILE="\$OMD_ROOT/tmp/run/orbvis.pid"
LOGFILE="\$OMD_ROOT/var/log/orbvis.log"
VENV="$VENV_DIR"
ENV_FILE="$ENV_FILE"
MKP_VERSION_FILE="$MKP_LIB/VERSION"
INSTALLED_VERSION_FILE="$ORBVIS_DIR/.installed-version"
SETUP_BIN="\$OMD_ROOT/local/bin/orbvis-setup"

# Trigger orbvis-setup automatically when a newer MKP has been installed but
# this site hasn't been refreshed yet (mkp update only replaces ~/local/, not
# the per-site venv / Apache conf / data layout). ORBVIS_NO_RESTART avoids the
# omd-recursion: orbvis-setup is told to skip its closing \`omd restart orbvis\`
# because that's exactly what we're inside of.
auto_refresh() {
  [[ -f "\$MKP_VERSION_FILE" && -x "\$SETUP_BIN" ]] || return 0
  local mkp_ver installed_ver
  mkp_ver="\$(cat "\$MKP_VERSION_FILE" 2>/dev/null || true)"
  installed_ver="\$(cat "\$INSTALLED_VERSION_FILE" 2>/dev/null || true)"
  [[ -n "\$mkp_ver" && "\$mkp_ver" != "\$installed_ver" ]] || return 0
  local banner="OrbVis: MKP version \$mkp_ver differs from installed \${installed_ver:-<none>}; running orbvis-setup..."
  echo ""
  echo "\$banner"
  echo "\$banner" >> "\$LOGFILE"
  if ! ORBVIS_NO_RESTART=1 "\$SETUP_BIN" >> "\$LOGFILE" 2>&1; then
    echo "WARN: orbvis-setup failed; see \$LOGFILE. Continuing with previous installation." >&2
    return 1
  fi
  echo "OrbVis refreshed to \$mkp_ver"
}

case "\$1" in
  start)
    if [[ -f "\$PIDFILE" ]] && kill -0 "\$(cat "\$PIDFILE")" 2>/dev/null; then
      echo "orbvis already running (pid \$(cat "\$PIDFILE"))"
      exit 0
    fi
    auto_refresh || true
    echo -n "Starting orbvis..."
    set -a; source "\$ENV_FILE"; set +a
    PORT="\${ORBVIS_PORT:-8420}"
    cd "$SERVER_DIR"  # extracted by orbvis-setup step 2
    # Schema is now ensured during the FastAPI lifespan (sqlite3.executescript).
    # setsid + nohup + </dev/null detaches from the calling session so SIGHUP
    # on \`omd su -i bash -c orbvis-setup\` exit doesn't take uvicorn down.
    setsid nohup "\$VENV/bin/python3" -m uvicorn app.main:app \\
      --host 127.0.0.1 --port "\$PORT" \\
      --log-level warning \\
      </dev/null >> "\$LOGFILE" 2>&1 &
    PID=\$!
    echo \$PID > "\$PIDFILE"
    sleep 1
    if kill -0 "\$PID" 2>/dev/null; then
      echo " OK (pid \$PID)"
    else
      rm -f "\$PIDFILE"
      echo " FAILED"
      echo "uvicorn died within 1s; see \$LOGFILE" >&2
      tail -20 "\$LOGFILE" >&2
      exit 1
    fi
    ;;
  stop)
    if [[ -f "\$PIDFILE" ]]; then
      PID="\$(cat "\$PIDFILE")"
      if kill -0 "\$PID" 2>/dev/null; then
        echo -n "Stopping orbvis (pid \$PID)..."
        kill "\$PID"
        for _ in \$(seq 1 20); do kill -0 "\$PID" 2>/dev/null || break; sleep 0.5; done
        echo " OK"
      fi
      rm -f "\$PIDFILE"
    else
      echo "orbvis not running"
    fi
    ;;
  restart) \$0 stop; \$0 start ;;
  status)
    if [[ -f "\$PIDFILE" ]] && kill -0 "\$(cat "\$PIDFILE")" 2>/dev/null; then
      echo "orbvis running (pid \$(cat "\$PIDFILE"))"; exit 0
    else
      echo "orbvis not running"; exit 1
    fi
    ;;
  *) echo "Usage: \$0 {start|stop|restart|status}"; exit 1 ;;
esac
EOF
  chmod +x "$INIT_TMP"
  mv -f "$INIT_TMP" "$INIT_SCRIPT"
  ln -sf "$INIT_SCRIPT" "$ROOT/etc/rc.d/85-orbvis" 2>/dev/null || true
  ok "OrbVis registered as OMD service"

  # 8. Stamp installed version so the init script can detect when a later
  # `mkp update` ships a newer VERSION and trigger an automatic refresh.
  if [[ -f "$MKP_LIB/VERSION" ]]; then
    cp "$MKP_LIB/VERSION" "$ORBVIS_DIR/.installed-version"
  fi

  # 9. Start services
  step "Reloading Apache"
  omd reload apache
  ok "Apache reloaded"

  # ORBVIS_NO_RESTART lets the init script call us during its own start
  # sequence without recursing into omd. The caller starts the backend itself.
  if [[ "${ORBVIS_NO_RESTART:-0}" == "1" ]]; then
    ok "OrbVis restart skipped (caller will start backend)"
  else
    step "Starting OrbVis"
    omd restart orbvis
    ok "OrbVis started"
  fi

  HOST="$(hostname -f 2>/dev/null || hostname)"
  echo ""
  echo -e "${GREEN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
  echo -e "${GREEN}${BOLD}  OrbVis setup complete!${RESET}"
  echo -e "${GREEN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
  echo ""
  echo "  Open in browser:  http://$HOST/$SITE/orbvis/"
  echo ""
  ;;

*)
  die "Unknown command: $CMD\nUsage: orbvis-setup [setup|uninstall]"
  ;;

esac
SETUP_SCRIPT
chmod +x "$TMPDIR/bin/orbvis-setup"
ok "orbvis-setup generated"

# ---------------------------------------------------------------------------
# 4. Collect file lists for the info manifest
# ---------------------------------------------------------------------------
step "Building file manifest"

# Paths relative to each category base directory. Use empty arrays when a
# category directory is absent (e.g. CMK 2.5 build has no web/ tree).
WEB_FILES=()
LIB_FILES=()
[[ -d "$TMPDIR/web" ]] && mapfile -t WEB_FILES < <(find "$TMPDIR/web" -type f | sed "s|$TMPDIR/web/||" | sort)
[[ -d "$TMPDIR/lib" ]] && mapfile -t LIB_FILES < <(find "$TMPDIR/lib" -type f | sed "s|$TMPDIR/lib/||" | sort)
BIN_FILES=("orbvis-setup")

ok "Manifest: ${#BIN_FILES[@]} bin, ${#WEB_FILES[@]} web, ${#LIB_FILES[@]} lib files"

# ---------------------------------------------------------------------------
# 5. Write info (Python dict) + info.json — both required by CMK
# ---------------------------------------------------------------------------
step "Writing MKP manifests"

# Build Python list literal from an array: 'a', 'b', ...
py_list() { printf "'%s', " "$@"; }

{
  echo "{"
  echo "  'author': 'OrbVis Project',"
  printf "  'description': 'OrbVis - modern monitoring visualization for Checkmk, successor to NagVis.\\\\n\\\\nBundles a small subset of cmk-frontend-vue (GPL-2.0); see NOTICE.\\\\n\\\\nAfter install, run orbvis-setup once as the site user.',\\n"
  echo "  'download_url': '',"
  echo "  'files': {"
  echo "    'bin': [$(py_list "${BIN_FILES[@]}")],"
  echo "    'lib': [$( ((${#LIB_FILES[@]})) && py_list "${LIB_FILES[@]}" )],"
  echo "    'web': [$( ((${#WEB_FILES[@]})) && py_list "${WEB_FILES[@]}" )],"
  echo "  },"
  echo "  'name': 'orbvis',"
  echo "  'title': 'OrbVis - Network Monitoring Visualization',"
  echo "  'version': '${VERSION}',"
  echo "  'version.min_required': '${MIN_REQUIRED}',"
  echo "  'version.packaged': '${PACKAGED}',"
  echo "  'version.usable_until': None,"
  echo "}"
} > "$TMPDIR/info"

python3 -c "import ast; ast.literal_eval(open('$TMPDIR/info').read())" \
  || die "info file failed ast.literal_eval validation"

# Generate info.json from info (CMK reads both)
python3 - "$TMPDIR/info" "$TMPDIR/info.json" << 'PY'
import ast, json, sys
data = ast.literal_eval(open(sys.argv[1]).read())
# Flatten files values to lists of strings
data["files"] = {k: [str(f) for f in v] for k, v in data["files"].items()}
open(sys.argv[2], "w").write(json.dumps(data))
PY

ok "Manifests written and validated"

# ---------------------------------------------------------------------------
# 6. Create per-category inner tars, then assemble .mkp
#
# MKP structure (as required by cmk.mkp_tool._mkp):
#   orbvis-X.mkp  (outer: tar.gz)
#   ├── info          – Python dict manifest
#   ├── info.json     – JSON manifest
#   ├── bin.tar       – uncompressed tar, extracted to local/bin/
#   ├── web.tar       – uncompressed tar, extracted to local/share/check_mk/web/
#   └── lib.tar       – uncompressed tar, extracted to local/lib/
# ---------------------------------------------------------------------------
step "Creating per-category inner tars"

tar cf "$TMPDIR/bin.tar" --dereference -C "$TMPDIR/bin" "${BIN_FILES[@]}"

# web.tar / lib.tar are written even when empty so the MKP has the expected
# archive set; CMK loads them by name.
INNER_TARS=("info" "info.json" "bin.tar")
if ((${#WEB_FILES[@]})); then
  tar cf "$TMPDIR/web.tar" --dereference -C "$TMPDIR/web" "${WEB_FILES[@]}"
  INNER_TARS+=("web.tar")
fi
if ((${#LIB_FILES[@]})); then
  tar cf "$TMPDIR/lib.tar" --dereference -C "$TMPDIR/lib" "${LIB_FILES[@]}"
  INNER_TARS+=("lib.tar")
fi

ok "Inner tars created (${INNER_TARS[*]})"

step "Creating ${MKP_NAME}"
tar czf "$MKP_OUT" -C "$TMPDIR" "${INNER_TARS[@]}"
ok "Created: $MKP_OUT"

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
SIZE="$(du -sh "$MKP_OUT" | cut -f1)"
echo ""
echo -e "${GREEN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "${GREEN}${BOLD}  MKP built successfully! ($SIZE)${RESET}"
echo -e "${GREEN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo ""
echo "  Package: $MKP_OUT"
echo ""
echo "  Install via Checkmk GUI:  Setup → Extension Packages → Upload"
echo "  Install via CLI:          mkp add $MKP_NAME && mkp enable orbvis"
echo ""
echo "  After installation, run once as the site user:"
echo "    su - <SITE> -c 'orbvis-setup'"
echo ""
