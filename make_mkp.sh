#!/bin/bash
# make_mkp.sh – Build OrbVis as a Checkmk 2.3 MKP package
#
# Usage:
#   ./make_mkp.sh [--version 1.2.3] [--out /path/to/output]
#
# Creates a self-contained .mkp that can be installed via:
#   mkp install orbvis-<version>.mkp
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

# GUI plugins (CMK 2.3 web/plugins/ layout)
mkdir -p "$TMPDIR/web/plugins/sidebar"
mkdir -p "$TMPDIR/web/plugins/wato"
cp "$SCRIPT_DIR/cmk_plugins_23/orbvis_sidebar.py" "$TMPDIR/web/plugins/sidebar/orbvis_sidebar.py"
cp "$SCRIPT_DIR/cmk_plugins_23/orbvis_menu.py"    "$TMPDIR/web/plugins/wato/orbvis_menu.py"

# Frontend build (stored in lib/orbvis/htdocs/ inside the MKP)
# Maps to: $OMD_ROOT/local/lib/orbvis/htdocs/
mkdir -p "$TMPDIR/lib/orbvis/htdocs"
cp -r "$SCRIPT_DIR/frontend/dist/." "$TMPDIR/lib/orbvis/htdocs/"

# Backend Python source (stored in lib/orbvis/server/)
# Maps to: $OMD_ROOT/local/lib/orbvis/server/
mkdir -p "$TMPDIR/lib/orbvis/server"
cp -r "$SCRIPT_DIR/backend/." "$TMPDIR/lib/orbvis/server/"

# Demo boards
mkdir -p "$TMPDIR/lib/orbvis/boards/backgrounds"
for f in "$SCRIPT_DIR/backend/boards/"demo*.json; do
  [[ -f "$f" ]] && cp "$f" "$TMPDIR/lib/orbvis/boards/"
done
if [[ -f "$SCRIPT_DIR/backend/boards/backgrounds/demo.svg" ]]; then
  cp "$SCRIPT_DIR/backend/boards/backgrounds/demo.svg" "$TMPDIR/lib/orbvis/boards/backgrounds/"
fi

ok "Files staged"

# ---------------------------------------------------------------------------
# 3. Generate orbvis-setup script
# ---------------------------------------------------------------------------
step "Generating orbvis-setup"
mkdir -p "$TMPDIR/bin"
cat > "$TMPDIR/bin/orbvis-setup" << 'SETUP_SCRIPT'
#!/bin/bash
# orbvis-setup – finalize OrbVis installation after MKP install
#
# Run as the OMD site user:
#   su - <SITE> -c "orbvis-setup"
#
# Or if already logged in as the site user:
#   orbvis-setup
#
set -euo pipefail

BOLD='\033[1m'; GREEN='\033[0;32m'; YELLOW='\033[0;33m'; RED='\033[0;31m'; RESET='\033[0m'
step()  { echo -e "  ${BOLD}▸ $*${RESET}"; }
ok()    { echo -e "  ${GREEN}✓ $*${RESET}"; }
warn()  { echo -e "  ${YELLOW}⚠ $*${RESET}"; }
die()   { echo -e "\n${RED}Error: $*${RESET}\n" >&2; exit 1; }

# Must run as the site user
SITE="${OMD_SITE:-}"
ROOT="${OMD_ROOT:-}"
[[ -z "$SITE" || -z "$ROOT" ]] && die "Run as the OMD site user (OMD_SITE / OMD_ROOT must be set).\nExample: su - <SITE> -c 'orbvis-setup'"

MKP_LIB="$ROOT/local/lib/orbvis"
[[ -d "$MKP_LIB" ]] || die "MKP library not found at $MKP_LIB\nDid you install the orbvis MKP first?"

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

echo ""
echo -e "${BOLD}OrbVis Post-Install Setup${RESET}"
echo "  Site: $SITE  ($ROOT)"
echo ""

# 1. Frontend: symlink/copy pre-built assets
step "Deploying frontend"
mkdir -p "$ORBVIS_DIR"
rm -rf "$HTDOCS_DIR"
cp -r "$MKP_LIB/htdocs" "$HTDOCS_DIR"
ok "Frontend deployed to $HTDOCS_DIR"

# 2. Demo boards (skip if already present)
step "Setting up board data"
mkdir -p "$BOARDS_DIR/backgrounds"
NEW_BOARDS=0
for f in "$MKP_LIB/boards/"*.json; do
  [[ -f "$f" ]] || continue
  fname="$(basename "$f")"
  if [[ ! -f "$BOARDS_DIR/$fname" ]]; then
    cp "$f" "$BOARDS_DIR/$fname"
    (( NEW_BOARDS++ )) || true
  fi
done
if [[ -f "$MKP_LIB/boards/backgrounds/demo.svg" && ! -f "$BOARDS_DIR/backgrounds/demo.svg" ]]; then
  cp "$MKP_LIB/boards/backgrounds/demo.svg" "$BOARDS_DIR/backgrounds/demo.svg"
fi
ok "Boards ready ($NEW_BOARDS new demo boards)"

# 3. Python virtualenv + backend
step "Setting up Python environment"
PYTHON3="$ROOT/bin/python3"
[[ -x "$PYTHON3" ]] || PYTHON3="$(command -v python3)"
if [[ ! -d "$VENV_DIR" ]]; then
  "$PYTHON3" -m venv --copies "$VENV_DIR"
fi
step "Installing backend dependencies"
"$VENV_DIR/bin/pip" install --quiet --upgrade pip
"$VENV_DIR/bin/pip" install --quiet -e "$MKP_LIB/server"
ok "Backend installed"

# 4. Configuration
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
  if omd config show LIVEPROXYD 2>/dev/null | grep -qi "^on$"; then
    LIVESTATUS_SOCKET="$ROOT/tmp/run/liveproxyd/$SITE.sock"
  fi
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

# 5. Apache configuration
step "Writing Apache configuration"
cat > "$APACHE_CONF" << EOF
# OrbVis – static frontend + backend proxy
# Auto-generated by orbvis-setup

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

# 6. OMD init script
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
    cd "$MKP_LIB/server"
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

# 7. Start services
step "Reloading Apache"
omd reload apache
ok "Apache reloaded"

step "Starting OrbVis"
omd restart orbvis
ok "OrbVis started"

# Done
HOST="$(hostname -f 2>/dev/null || hostname)"
echo ""
echo -e "${GREEN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "${GREEN}${BOLD}  OrbVis setup complete!${RESET}"
echo -e "${GREEN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo ""
echo "  Open in browser:  http://$HOST/$SITE/orbvis/"
echo ""
SETUP_SCRIPT
chmod +x "$TMPDIR/bin/orbvis-setup"
ok "orbvis-setup generated"

# ---------------------------------------------------------------------------
# 4. Collect file lists for the info manifest
# ---------------------------------------------------------------------------
step "Building file manifest"

WEB_FILES=()
while IFS= read -r f; do
  WEB_FILES+=("\"${f#$TMPDIR/web/}\"")
done < <(find "$TMPDIR/web" -type f | sort)

LIB_FILES=()
while IFS= read -r f; do
  LIB_FILES+=("\"${f#$TMPDIR/lib/}\"")
done < <(find "$TMPDIR/lib" -type f | sort)

BIN_FILES=("\"orbvis-setup\"")

web_json="$(IFS=,; echo "${WEB_FILES[*]}" | sed 's/,/,\n      /g')"
lib_json="$(IFS=,; echo "${LIB_FILES[*]}" | sed 's/,/,\n      /g')"
bin_json="$(IFS=,; echo "${BIN_FILES[*]}")"

ok "Manifest built (${#WEB_FILES[@]} web, ${#LIB_FILES[@]} lib, ${#BIN_FILES[@]} bin files)"

# ---------------------------------------------------------------------------
# 5. Write info JSON
# ---------------------------------------------------------------------------
step "Writing MKP info"
cat > "$TMPDIR/info" << EOF
{
  "author": "OrbVis Project",
  "description": "OrbVis - Network monitoring visualization for Checkmk.\n\nAfter installation run once as the site user:\n  su - <SITE> -c \"orbvis-setup\"",
  "download_url": "",
  "files": {
    "bin": [
      $bin_json
    ],
    "lib": [
      $lib_json
    ],
    "web": [
      $web_json
    ]
  },
  "name": "orbvis",
  "title": "OrbVis - Network Monitoring Visualization",
  "version": "${VERSION}",
  "version.min_required": "2.3.0",
  "version.packaged": "2.3.0p1",
  "version.usable_until": null
}
EOF
ok "info written"

# ---------------------------------------------------------------------------
# 6. Package into .mkp (tar.gz)
# ---------------------------------------------------------------------------
step "Creating ${MKP_NAME}"
cd "$TMPDIR"
tar czf "$MKP_OUT" .
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
echo "  Install via CLI:          mkp install $MKP_NAME"
echo ""
echo "  After installation, run once as the site user:"
echo "    su - <SITE> -c 'orbvis-setup'"
echo ""
