#!/bin/bash
# make_mkp.sh – Build OrbVis as a Checkmk 2.3 MKP package
#
# Usage:
#   ./make_mkp.sh [--version 1.2.3] [--out /path/to/output]
#
# Creates a self-contained .mkp that can be installed via:
#   mkp add orbvis-<version>.mkp && mkp enable orbvis
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
VERSION="1.0.0"
OUT_DIR="$(pwd)"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --version) VERSION="$2"; shift 2 ;;
    --out)     OUT_DIR="$2";  shift 2 ;;
    *) die "Unknown argument: $1" ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MKP_NAME="orbvis-${VERSION}.mkp"
MKP_OUT="${OUT_DIR}/${MKP_NAME}"
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

echo ""
echo -e "${BOLD}Building OrbVis MKP v${VERSION}${RESET}"
echo ""

# ---------------------------------------------------------------------------
# 1. Build frontend (relative base path → works at any /<SITE>/orbvis/ URL)
# ---------------------------------------------------------------------------
step "Building frontend (relative base path)"
NPM="$(command -v npm 2>/dev/null || true)"
[[ -z "$NPM" ]] && die "npm not found. Install Node.js >= 18."
cd "$SCRIPT_DIR/frontend"
npm install --silent
VITE_BASE_PATH=./ npm run build -- --base='./' --logLevel=warn
ok "Frontend built"

# ---------------------------------------------------------------------------
# 2. Stage directory structure for MKP
# ---------------------------------------------------------------------------
step "Staging MKP structure"
mkdir -p "$TMPDIR/web/plugins/sidebar" "$TMPDIR/web/plugins/wato" "$TMPDIR/lib/orbvis"

# GUI plugins (CMK 2.3 web/plugins/ layout)
cp "$SCRIPT_DIR/cmk_plugins_23/orbvis_sidebar.py"     "$TMPDIR/web/plugins/sidebar/orbvis_sidebar.py"
cp "$SCRIPT_DIR/cmk_plugins_23/orbvis_menu.py"        "$TMPDIR/web/plugins/wato/orbvis_menu.py"
cp "$SCRIPT_DIR/cmk_plugins_23/orbvis_permissions.py" "$TMPDIR/web/plugins/wato/orbvis_permissions.py"

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
  --exclude="boards" \
  --exclude="images" \
  -C "$SCRIPT_DIR/backend" .

# CHANGELOG.md and VERSION live in the repo root; copy them next to the
# server tarball so the backend (which searches lib/orbvis/{,server/}) can
# find them at runtime — otherwise the in-app changelog modal stays empty.
cp "$SCRIPT_DIR/CHANGELOG.md" "$TMPDIR/lib/orbvis/CHANGELOG.md"
cp "$SCRIPT_DIR/VERSION"      "$TMPDIR/lib/orbvis/VERSION"

# Demo boards: tarball → lib/orbvis/boards.tar.gz
mapfile -t _BOARD_FILES < <(cd "$SCRIPT_DIR/backend" && find boards -name "demo*.json" -o -name "demo.svg" 2>/dev/null | sort)
tar czf "$TMPDIR/lib/orbvis/boards.tar.gz" \
  -C "$SCRIPT_DIR/backend" \
  "${_BOARD_FILES[@]}"

ok "Files staged (frontend + backend + boards bundled as tarballs)"

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
BACKENDS_FILE="$ORBVIS_DIR/backends.json"
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
  echo "                     $BACKENDS_FILE"
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

  # 3. Demo boards (only seed on fresh install — skip if any *.json already exists)
  step "Setting up board data"
  mkdir -p "$BOARDS_DIR/backgrounds"
  if compgen -G "$BOARDS_DIR/*.json" > /dev/null; then
    ok "Boards ready (existing boards detected, skipping demo seed)"
  else
    TMPBOARDS="$(mktemp -d)"
    tar xzf "$MKP_LIB/boards.tar.gz" -C "$TMPBOARDS"
    NEW_BOARDS=0
    for f in "$TMPBOARDS/boards/"*.json; do
      [[ -f "$f" ]] || continue
      cp "$f" "$BOARDS_DIR/$(basename "$f")"
      NEW_BOARDS=$(( NEW_BOARDS + 1 ))
    done
    [[ -f "$TMPBOARDS/boards/backgrounds/demo.svg" && ! -f "$BOARDS_DIR/backgrounds/demo.svg" ]] && \
      cp "$TMPBOARDS/boards/backgrounds/demo.svg" "$BOARDS_DIR/backgrounds/demo.svg"
    rm -rf "$TMPBOARDS"
    ok "Boards ready ($NEW_BOARDS demo board(s) installed)"
  fi

  # 4. Python virtualenv + backend
  step "Setting up Python environment"
  PYTHON3="$ROOT/bin/python3"
  [[ -x "$PYTHON3" ]] || PYTHON3="$(command -v python3)"
  if [[ ! -d "$VENV_DIR" ]]; then
    "$PYTHON3" -m venv --copies "$VENV_DIR"
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
BACKENDS_FILE=$BACKENDS_FILE
DATABASE_URL=sqlite+aiosqlite:///$DB_FILE
SECRET_KEY=$SECRET_KEY
STATE_REFRESH_INTERVAL=15
CHECKMK_HTPASSWD=$ROOT/etc/htpasswd
CHECKMK_OMD_ROOT=$ROOT
CHECKMK_SITE=$SITE
EOF

  if [[ ! -f "$BACKENDS_FILE" ]]; then
    cat > "$BACKENDS_FILE" << EOF
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
    ok "Configuration written (existing backends.json kept)"
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

# Paths relative to each category base directory
mapfile -t WEB_FILES < <(find "$TMPDIR/web" -type f | sed "s|$TMPDIR/web/||" | sort)
mapfile -t LIB_FILES < <(find "$TMPDIR/lib" -type f | sed "s|$TMPDIR/lib/||" | sort)
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
  printf "  'description': 'OrbVis monitoring visualization.\\\\n\\\\nAfter install run: su - <SITE> -c orbvis-setup',\\n"
  echo "  'download_url': '',"
  echo "  'files': {"
  echo "    'bin': [$(py_list "${BIN_FILES[@]}")],"
  echo "    'lib': [$(py_list "${LIB_FILES[@]}")],"
  echo "    'web': [$(py_list "${WEB_FILES[@]}")],"
  echo "  },"
  echo "  'name': 'orbvis',"
  echo "  'title': 'OrbVis - Network Monitoring Visualization',"
  echo "  'version': '${VERSION}',"
  echo "  'version.min_required': '2.3.0',"
  echo "  'version.packaged': '2.3.0p1',"
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
tar cf "$TMPDIR/web.tar" --dereference -C "$TMPDIR/web" "${WEB_FILES[@]}"
tar cf "$TMPDIR/lib.tar" --dereference -C "$TMPDIR/lib" "${LIB_FILES[@]}"

ok "Inner tars created (bin.tar, web.tar, lib.tar)"

step "Creating ${MKP_NAME}"
tar czf "$MKP_OUT" -C "$TMPDIR" info info.json bin.tar web.tar lib.tar
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
