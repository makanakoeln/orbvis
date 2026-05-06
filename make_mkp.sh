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
  VITE_BASE_PATH=./ npm run build -- --base='./' --logLevel=warn
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
# orbvis-setup extracts it to $OMD_ROOT/local/share/orbvis/htdocs/
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

# CHANGELOG.md and VERSION live in the repo root; copy them next to the
# server tarball so the backend (which searches lib/orbvis/{,server/}) can
# find them at runtime — otherwise the in-app changelog modal stays empty.
cp "$SCRIPT_DIR/CHANGELOG.md" "$TMPDIR/lib/orbvis/CHANGELOG.md"
cp "$SCRIPT_DIR/VERSION"      "$TMPDIR/lib/orbvis/VERSION"

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

MKP_LIB="$ROOT/local/lib/orbvis"
ORBVIS_DIR="$ROOT/local/share/orbvis"
HTDOCS_DIR="$ORBVIS_DIR/htdocs"
BOARDS_DIR="$ORBVIS_DIR/boards"
ENV_FILE="$ORBVIS_DIR/.env"
CONNECTIONS_FILE="$ORBVIS_DIR/connections.json"
DB_FILE="$ORBVIS_DIR/orbvis.db"
VENV_DIR="$ORBVIS_DIR/venv"
APACHE_CONF="$ROOT/etc/apache/conf.d/orbvis.conf"
INIT_SCRIPT="$ROOT/etc/init.d/orbvis"
BACKEND_PORT=8420
LIVESTATUS_SOCKET="$ROOT/tmp/run/live"

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
  rm -rf "$MKP_LIB/server"
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

  # 1. Frontend: extract pre-built tarball
  step "Deploying frontend"
  mkdir -p "$HTDOCS_DIR"
  rm -rf "${HTDOCS_DIR:?}"/*
  tar xzf "$MKP_LIB/htdocs.tar.gz" -C "$HTDOCS_DIR"
  ok "Frontend deployed to $HTDOCS_DIR"

  # 2. Backend source: extract tarball
  step "Extracting backend source"
  mkdir -p "$MKP_LIB/server"
  tar xzf "$MKP_LIB/server.tar.gz" -C "$MKP_LIB/server"
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

  # Checkmk 2.6+ ships a sitecustomize.py that imports cmk.licensing.* whenever
  # OMD_ROOT is set. Inside a venv `sys.executable` points at the venv binary,
  # so sitecustomize cannot derive the OMD lib path on its own — we have to
  # surface $OMD_ROOT/lib/python3 via PYTHONPATH for both venv creation and
  # every subsequent invocation of the venv python (see init script below).
  export PYTHONPATH="$ROOT/lib/python3${PYTHONPATH:+:$PYTHONPATH}"

  if [[ ! -d "$VENV_DIR" ]]; then
    "$PYTHON3" -m venv --symlinks "$VENV_DIR"
  fi
  if [[ ! -L "$VENV_DIR/bin/python3" ]]; then
    ln -sf "$PYTHON3" "$VENV_DIR/bin/python3"
  fi
  step "Installing backend dependencies"
  "$VENV_DIR/bin/pip" install --quiet --upgrade pip
  "$VENV_DIR/bin/pip" install --quiet "$MKP_LIB/server"
  ok "Backend installed"

  # 5. Configuration
  step "Writing configuration"
  EXISTING_SECRET=""
  [[ -f "$ENV_FILE" ]] && EXISTING_SECRET=$(grep -E '^SECRET_KEY=' "$ENV_FILE" | head -1 | cut -d= -f2- || true)
  SECRET_KEY="${EXISTING_SECRET:-$("$PYTHON3" -c 'import secrets; print(secrets.token_hex(32))')}"

  cat > "$ENV_FILE" << EOF
BOARDS_DIR=$BOARDS_DIR
CONNECTIONS_FILE=$CONNECTIONS_FILE
DATABASE_URL=sqlite+aiosqlite:///$DB_FILE
SECRET_KEY=$SECRET_KEY
STATE_REFRESH_INTERVAL=15
CHECKMK_HTPASSWD=$ROOT/etc/htpasswd
CHECKMK_OMD_ROOT=$ROOT
CHECKMK_SITE=$SITE
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

  # Locate mod_proxy.so — CMK 2.4 bundles its own, CMK 2.3 uses the system Apache binary
  # and therefore needs the system module path (Ubuntu/Debian: /usr/lib/apache2/modules/).
  PROXY_SO=""
  PROXY_HTTP_SO=""
  for _dir in \
      "$ROOT/lib/apache/modules" \
      "/usr/lib/apache2/modules" \
      "/usr/lib64/httpd/modules" \
      "/usr/lib/httpd/modules"; do
    if [[ -f "$_dir/mod_proxy.so" && -f "$_dir/mod_proxy_http.so" ]]; then
      PROXY_SO="$_dir/mod_proxy.so"
      PROXY_HTTP_SO="$_dir/mod_proxy_http.so"
      break
    fi
  done

  if [[ -z "$PROXY_SO" ]]; then
    warn "mod_proxy.so not found — API proxy will be disabled. Backend API will be unreachable."
  fi

  cat > "$APACHE_CONF" << EOF
# OrbVis – static frontend + backend proxy
# Auto-generated by orbvis-setup

# mod_proxy is not bundled in all OMD versions — load from detected path
<IfModule !mod_proxy.c>
    LoadModule proxy_module $PROXY_SO
</IfModule>
<IfModule !mod_proxy_http.c>
    LoadModule proxy_http_module $PROXY_HTTP_SO
</IfModule>

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

<Location /$SITE/orbvis/api>
    ProxyPass        http://127.0.0.1:$BACKEND_PORT/api
    ProxyPassReverse http://127.0.0.1:$BACKEND_PORT/api
</Location>

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
  cat > "$INIT_SCRIPT" << EOF
#!/bin/bash
# OMD init script for OrbVis backend

PIDFILE="\$OMD_ROOT/tmp/run/orbvis.pid"
LOGFILE="\$OMD_ROOT/var/log/orbvis.log"
VENV="$VENV_DIR"
PORT=$BACKEND_PORT
ENV_FILE="$ENV_FILE"

# Checkmk 2.6+ sitecustomize imports cmk.licensing.* on every Python start;
# the venv python does not see \$OMD_ROOT/lib/python3 unless we add it.
export PYTHONPATH="\$OMD_ROOT/lib/python3\${PYTHONPATH:+:\$PYTHONPATH}"

case "\$1" in
  start)
    if [[ -f "\$PIDFILE" ]] && kill -0 "\$(cat "\$PIDFILE")" 2>/dev/null; then
      echo "orbvis already running (pid \$(cat "\$PIDFILE"))"
      exit 0
    fi
    echo -n "Starting orbvis..."
    set -a; source "\$ENV_FILE"; set +a
    cd "$MKP_LIB/server"  # extracted by orbvis-setup step 2
    "\$VENV/bin/python3" -m alembic upgrade head >> "\$LOGFILE" 2>&1
    "\$VENV/bin/uvicorn" app.main:app \\
      --host 127.0.0.1 --port \$PORT \\
      --log-level warning \\
      >> "\$LOGFILE" 2>&1 &
    echo \$! > "\$PIDFILE"
    echo " OK (pid \$(cat "\$PIDFILE"))"
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
  chmod +x "$INIT_SCRIPT"
  ln -sf "$INIT_SCRIPT" "$ROOT/etc/rc.d/85-orbvis" 2>/dev/null || true
  ok "OrbVis registered as OMD service"

  # 8. Start services
  step "Reloading Apache"
  omd reload apache
  ok "Apache reloaded"

  step "Starting OrbVis"
  omd restart orbvis
  ok "OrbVis started"

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
  printf "  'description': 'OrbVis - modern monitoring visualization for Checkmk, successor to NagVis.\\\\n\\\\nAfter install, run orbvis-setup once as the site user.',\\n"
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
