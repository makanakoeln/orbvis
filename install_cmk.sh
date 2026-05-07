#!/bin/bash
# install_cmk.sh – Deploy/remove OrbVis in an OMD/Checkmk site
# Usage: ./install_cmk.sh <site-name> [install|remove]
# Run as a normal user; sudo is invoked automatically for privileged steps.
set -euo pipefail

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
BOLD='\033[1m'
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
RESET='\033[0m'

step()  { echo -e "  ${BOLD}▸ $*${RESET}"; }
ok()    { echo -e "  ${GREEN}✓ $*${RESET}"; }
warn()  { echo -e "  ${YELLOW}⚠ $*${RESET}"; }
die()   { echo -e "\n${RED}Error: $*${RESET}\n" >&2; exit 1; }
header(){ echo -e "\n${BOLD}$*${RESET}"; }

# All verbose output goes here; shown only on failure
LOG_FILE="/tmp/orbvis_install_${1:-unknown}.log"
# Redirect all command output to log unless already shown
quietly() { "$@" >> "$LOG_FILE" 2>&1; }

# ---------------------------------------------------------------------------
# OS detection
# ---------------------------------------------------------------------------
_detect_os() {
  OS_FAMILY="unknown"
  if [[ -f /etc/os-release ]]; then
    local id
    # shellcheck source=/dev/null
    id="$(. /etc/os-release; echo "${ID:-}")"
    case "$id" in
      ubuntu|debian)                  OS_FAMILY=debian ;;
      rhel|centos|rocky|almalinux|ol) OS_FAMILY=rhel ;;
      sles|opensuse*|suse)            OS_FAMILY=suse ;;
    esac
  fi
}
_detect_os

# ---------------------------------------------------------------------------
# Arguments
# ---------------------------------------------------------------------------
SITE="${1:-}"
ACTION="${2:-install}"

if [[ -z "$SITE" ]] || [[ "$ACTION" != "install" && "$ACTION" != "remove" ]]; then
  echo "Usage: $0 <site-name> [install|remove]"
  exit 1
fi

[[ "$EUID" -eq 0 ]] && die "Run this script as a normal user, not as root."

SITE_ROOT="/omd/sites/$SITE"
[[ -d "$SITE_ROOT" ]] || die "OMD site '$SITE' not found."

# Detect CMK version from site symlink (e.g. ../../versions/2.4.0p24.cre → 2.4.0p24)
CMK_VERSION_RAW=$(readlink "$SITE_ROOT/version" 2>/dev/null || true)
CMK_VERSION=$(basename "${CMK_VERSION_RAW}" | sed 's/\.[a-z]*$//' 2>/dev/null || echo "unknown")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ORBVIS_DIR="$SITE_ROOT/local/share/orbvis"
HTDOCS_DIR="$ORBVIS_DIR/htdocs"
BOARDS_DIR="$ORBVIS_DIR/boards"
ENV_FILE="$ORBVIS_DIR/.env"
CONNECTIONS_FILE="$ORBVIS_DIR/connections.json"
DB_FILE="$ORBVIS_DIR/orbvis.db"
# Determine port: reuse existing from .env if present, else pick the lowest
# free port from 8420 upward. Skip ports already reserved by other OrbVis
# installs on this host (their .env may pin a port even while the site is
# stopped) as well as anything currently bound in the live socket table.
BACKEND_PORT=""
if sudo test -f "$ENV_FILE" 2>/dev/null; then
  BACKEND_PORT=$(sudo grep -E '^ORBVIS_PORT=' "$ENV_FILE" 2>/dev/null | head -1 | cut -d= -f2- || true)
fi
if [[ -z "$BACKEND_PORT" ]]; then
  declare -A RESERVED_PORTS=()
  for envf in /omd/sites/*/local/share/orbvis/.env; do
    [[ -f "$envf" && "$envf" != "$ENV_FILE" ]] || continue
    p=$(sudo grep -E '^ORBVIS_PORT=' "$envf" 2>/dev/null | head -1 | cut -d= -f2- || true)
    [[ -n "$p" ]] && RESERVED_PORTS[$p]=1
  done
  BACKEND_PORT=8420
  while (( BACKEND_PORT < 8500 )); do
    if [[ -z "${RESERVED_PORTS[$BACKEND_PORT]:-}" ]] \
       && ! ss -tlnH "( sport = :$BACKEND_PORT )" 2>/dev/null | grep -q .; then
      break
    fi
    (( BACKEND_PORT++ ))
  done
  (( BACKEND_PORT < 8500 )) || die "No free port available in 8420-8499 for OrbVis backend."
fi
BASE_PATH="/$SITE/orbvis"
LIVESTATUS_SOCKET="$SITE_ROOT/tmp/run/live"
VENV_DIR="$ORBVIS_DIR/venv"
CMK_PLUGINS_SRC="$SCRIPT_DIR/cmk_plugins"
CMK_PLUGINS_DST="$ORBVIS_DIR/cmk_plugins"
APACHE_CONF="$SITE_ROOT/etc/apache/conf.d/orbvis.conf"
INIT_SCRIPT="$SITE_ROOT/etc/init.d/orbvis"

# ---------------------------------------------------------------------------
# Prerequisites
# ---------------------------------------------------------------------------
NPM=""
if [[ ! -d "$SCRIPT_DIR/htdocs" ]]; then
  NPM="$(command -v npm 2>/dev/null || true)"
  if [[ -z "$NPM" ]]; then
    case "$OS_FAMILY" in
      rhel) NODE_HINT="sudo dnf module enable nodejs:20 && sudo dnf install nodejs" ;;
      suse) NODE_HINT="sudo zypper install nodejs20" ;;
      *)    NODE_HINT="sudo apt install nodejs npm" ;;
    esac
    die "npm not found. Install Node.js >= 18:\n  $NODE_HINT"
  fi
  NODE_MAJOR="$(node --version 2>/dev/null | sed 's/v\([0-9]*\).*/\1/')"
  [[ -z "$NODE_MAJOR" || "$NODE_MAJOR" -lt 18 ]] && \
    die "Node.js >= 18 required (found: $(node --version 2>/dev/null || echo none))."
fi

if [[ -x "$SITE_ROOT/bin/python3" ]]; then
  PYTHON3="$SITE_ROOT/bin/python3"
else
  PYTHON3="$(command -v python3 2>/dev/null || true)"
  [[ -z "$PYTHON3" ]] && die "python3 not found."
fi


# ---------------------------------------------------------------------------
# Sudo – authenticate once up front
# ---------------------------------------------------------------------------
echo ""
echo "sudo is required for privileged steps. You may be prompted for your password."
sudo -v

# ---------------------------------------------------------------------------
# REMOVE
# ---------------------------------------------------------------------------
if [[ "$ACTION" == "remove" ]]; then
  header "Removing OrbVis from site '$SITE'"
  : > "$LOG_FILE"

  step "Stopping OrbVis backend"
  quietly sudo -u "$SITE" omd stop orbvis 2>/dev/null || true
  ok "Backend stopped"

  step "Removing files"
  quietly sudo rm -f "$APACHE_CONF" "$INIT_SCRIPT" "$SITE_ROOT/etc/rc.d/85-orbvis"
  quietly sudo -u "$SITE" "$PYTHON3" -m pip uninstall -y orbvis-cmk 2>/dev/null || true
  quietly sudo rm -rf "$HTDOCS_DIR" "$VENV_DIR" "$ORBVIS_DIR/src" "$CMK_PLUGINS_DST" "$DB_FILE" "$ENV_FILE" "$CONNECTIONS_FILE"
  ok "Files removed"

  step "Reloading Apache"
  quietly sudo omd reload "$SITE" apache
  ok "Apache reloaded"

  echo ""
  echo -e "${GREEN}${BOLD}OrbVis removed from site '$SITE'.${RESET}"
  warn "Board files were kept in: $BOARDS_DIR"
  echo "  To remove them as well: sudo rm -rf $BOARDS_DIR"
  echo ""
  exit 0
fi

# ---------------------------------------------------------------------------
# INSTALL
# ---------------------------------------------------------------------------
header "Installing OrbVis into Checkmk site '$SITE'"
echo "  Site:    $SITE_ROOT"
echo "  CMK:     $CMK_VERSION"
echo "  URL:     https://$(hostname -f 2>/dev/null || hostname)$BASE_PATH/"
: > "$LOG_FILE"

# 1. Frontend
if [[ -d "$SCRIPT_DIR/htdocs" ]]; then
  step "Deploying pre-built frontend"
  quietly sudo rm -rf "$HTDOCS_DIR"
  quietly sudo mkdir -p "$HTDOCS_DIR"
  quietly sudo cp -r "$SCRIPT_DIR/htdocs/." "$HTDOCS_DIR/"
  ok "Frontend deployed"
else
  step "Building frontend"
  cd "$SCRIPT_DIR/frontend"
  quietly "$NPM" install
  quietly "$NPM" run build -- --base="$BASE_PATH/"
  quietly sudo rm -rf "$HTDOCS_DIR"
  quietly sudo mkdir -p "$HTDOCS_DIR"
  quietly sudo cp -r "$SCRIPT_DIR/frontend/dist/." "$HTDOCS_DIR/"
  ok "Frontend built and deployed"
fi

# 2. Data directories + demo boards
step "Setting up data directories"
IMAGES_DIR="$(dirname "$BOARDS_DIR")/images"
quietly sudo mkdir -p "$BOARDS_DIR/backgrounds" "$IMAGES_DIR"
# Only seed demo boards on a truly fresh install (no existing *.json in BOARDS_DIR)
if compgen -G "$BOARDS_DIR/*.json" > /dev/null; then
  ok "Directories ready (existing boards detected, skipping demo seed)"
else
  NEW_BOARDS=0
  for demo in "$SCRIPT_DIR/backend/app/_seed_boards/"demo*.json; do
    quietly sudo cp "$demo" "$BOARDS_DIR/$(basename "$demo")"
    (( NEW_BOARDS++ )) || true
  done
  if ! sudo test -f "$BOARDS_DIR/backgrounds/demo.svg"; then
    quietly sudo cp "$SCRIPT_DIR/backend/app/_seed_boards/backgrounds/demo.svg" "$BOARDS_DIR/backgrounds/demo.svg"
  fi
  ok "Directories ready ($NEW_BOARDS demo board(s) installed)"
fi

# 3. Python virtualenv + dependencies
step "Setting up Python environment"
if sudo test -d "$VENV_DIR"; then
  ok "Virtualenv already exists, skipping creation"
else
  quietly sudo "$PYTHON3" -m venv --symlinks "$VENV_DIR"
fi
# Ensure venv python3 is a symlink so the OMD Python's RPATH is preserved.
# When venv copies the binary instead of symlinking, libpython3.13 can't be
# found at runtime because the relative RPATH no longer resolves correctly.
if [[ ! -L "$VENV_DIR/bin/python3" ]]; then
  quietly sudo ln -sf "$PYTHON3" "$VENV_DIR/bin/python3"
fi
if ! sudo test -f "$VENV_DIR/bin/pip"; then
  # CMK 2.5+ builds Python without ensurepip wheel; bootstrap pip from site
  quietly sudo "$SITE_ROOT/bin/pip3" install --prefix="$VENV_DIR" pip \
    || die "Cannot install pip into virtualenv (tried $SITE_ROOT/bin/pip3)."
fi
step "Installing backend dependencies"
quietly sudo "$VENV_DIR/bin/pip" install --quiet --upgrade pip
# rsync rather than cp -r so dev artefacts (backends.json, connections.json,
# *.db, boards/) from the source checkout never leak into the installed copy.
quietly sudo rsync -a --delete \
  --exclude='backends.json' \
  --exclude='connections.json' \
  --exclude='boards/' \
  --exclude='*.db' \
  --exclude='*.db-shm' \
  --exclude='*.db-wal' \
  --exclude='__pycache__' \
  --exclude='.venv' \
  --exclude='.pytest_cache' \
  --exclude='.mypy_cache' \
  "$SCRIPT_DIR/backend/" "$ORBVIS_DIR/src/"
quietly sudo cp "$SCRIPT_DIR/VERSION" "$ORBVIS_DIR/VERSION"
quietly sudo cp "$SCRIPT_DIR/CHANGELOG.md" "$ORBVIS_DIR/CHANGELOG.md"
quietly sudo "$VENV_DIR/bin/pip" install --quiet -e "$ORBVIS_DIR/src"
# Clean up dev artefacts that earlier installs may have left behind in src/.
quietly sudo rm -f "$ORBVIS_DIR/src/backends.json" "$ORBVIS_DIR/src/connections.json"
ok "Backend dependencies installed"

# 4. Configuration
step "Writing configuration"
EXISTING_SECRET=""
if sudo test -f "$ENV_FILE"; then
  EXISTING_SECRET=$(sudo grep -E '^SECRET_KEY=' "$ENV_FILE" | head -1 | cut -d= -f2- || true)
fi
SECRET_KEY="${EXISTING_SECRET:-$("$PYTHON3" -c 'import secrets; print(secrets.token_hex(32))')}"

sudo tee "$ENV_FILE" > /dev/null <<EOF
BOARDS_DIR=$BOARDS_DIR
CONNECTIONS_FILE=$CONNECTIONS_FILE
DATABASE_URL=sqlite+aiosqlite:///$DB_FILE
SECRET_KEY=$SECRET_KEY
STATE_REFRESH_INTERVAL=15
CHECKMK_HTPASSWD=$SITE_ROOT/etc/htpasswd
CHECKMK_OMD_ROOT=$SITE_ROOT
CHECKMK_SITE=$SITE
ORBVIS_PORT=$BACKEND_PORT
EOF

if sudo test -f "$CONNECTIONS_FILE"; then
  ok "Configuration written (existing connections.json kept)"
else
  sudo tee "$CONNECTIONS_FILE" > /dev/null <<EOF
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
fi

# 5. Apache config
step "Writing Apache configuration"

# Detect Apache modules directory (Debian/Ubuntu vs RHEL/CentOS)
APACHE_MODULES_DIR=""
for candidate in \
    /usr/lib/apache2/modules \
    /usr/lib64/httpd/modules \
    /usr/lib/httpd/modules \
    /usr/lib/x86_64-linux-gnu/apache2/modules; do
  if [[ -f "$candidate/mod_proxy.so" ]]; then
    APACHE_MODULES_DIR="$candidate"
    break
  fi
done
[[ -z "$APACHE_MODULES_DIR" ]] && die "Cannot find mod_proxy.so. Install Apache proxy modules:\n  sudo apt install libapache2-mod-proxy-html"

# Detect Swagger-UI bundled with the Checkmk site. Only Swagger-UI 5.x supports
# OpenAPI 3.1, which is what FastAPI emits. Older sites (2.3/2.4) ship
# swagger-ui-3 (Swagger-UI 3.x) which can only render OpenAPI 3.0.x and would
# fail with "Unable to render this definition" — so those are skipped here.
SWAGGER_UI_DIR=""
for candidate in "$SITE_ROOT"/share/check_mk/web/htdocs/openapi/swagger-ui-5.*; do
  if [[ -f "$candidate/swagger-ui-bundle.js" ]]; then
    SWAGGER_UI_DIR="$candidate"
    break
  fi
done

SWAGGER_UI_ALIAS=""
SWAGGER_UI_PROXYBYPASS=""
if [[ -n "$SWAGGER_UI_DIR" ]]; then
  # Alias must precede the broader '/<SITE>/orbvis' Alias (first match wins).
  # The ProxyPass exclusion (top-level form, '!') must precede the /api
  # ProxyPass directive — first-match-wins.
  SWAGGER_UI_ALIAS="
# Swagger-UI assets shipped with this Checkmk site
Alias /$SITE/orbvis/api/swagger-ui $SWAGGER_UI_DIR
<Directory $SWAGGER_UI_DIR>
    Options -Indexes +FollowSymLinks
    AllowOverride None
    Require all granted
</Directory>
"
  SWAGGER_UI_PROXYBYPASS="ProxyPass        /$SITE/orbvis/api/swagger-ui  !"
fi

sudo tee "$APACHE_CONF" > /dev/null <<EOF
# OrbVis – static frontend + backend proxy
# Auto-generated by install_cmk.sh

<IfModule !mod_proxy.c>
    LoadModule proxy_module $APACHE_MODULES_DIR/mod_proxy.so
</IfModule>
<IfModule !mod_proxy_http.c>
    LoadModule proxy_http_module $APACHE_MODULES_DIR/mod_proxy_http.so
</IfModule>
<IfModule !mod_proxy_wstunnel.c>
    LoadModule proxy_wstunnel_module $APACHE_MODULES_DIR/mod_proxy_wstunnel.so
</IfModule>
<IfModule !mod_headers.c>
    LoadModule headers_module $APACHE_MODULES_DIR/mod_headers.so
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
    # Never cache index.html so browsers always fetch the latest asset hashes
    <FilesMatch "^index\.html$">
        Header set Cache-Control "no-store, no-cache, must-revalidate"
        Header set Pragma "no-cache"
        Header set Expires "0"
    </FilesMatch>
</Directory>

# WebSocket and HTTP proxies declared at the top level: ProxyPass directives
# here use strict first-match-wins. Order matters: WS sub-path and any
# exclusions (Swagger-UI assets) must precede the broader /api ProxyPass.
$SWAGGER_UI_PROXYBYPASS
ProxyPass        /$SITE/orbvis/api/v1/ws  ws://127.0.0.1:$BACKEND_PORT/api/v1/ws
ProxyPassReverse /$SITE/orbvis/api/v1/ws  ws://127.0.0.1:$BACKEND_PORT/api/v1/ws
ProxyPass        /$SITE/orbvis/api        http://127.0.0.1:$BACKEND_PORT/api
ProxyPassReverse /$SITE/orbvis/api        http://127.0.0.1:$BACKEND_PORT/api

<Location /$SITE/orbvis/api>
    <IfModule mod_allowmethods.c>
        AllowMethods GET POST PUT PATCH DELETE OPTIONS HEAD
    </IfModule>
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
sudo tee "$INIT_SCRIPT" > /dev/null <<EOF
#!/bin/bash
# OMD init script for OrbVis backend

PIDFILE="\$OMD_ROOT/tmp/run/orbvis.pid"
LOGFILE="\$OMD_ROOT/var/log/orbvis.log"
VENV="$VENV_DIR"
APP="app.main:app"
ENV_FILE="$ENV_FILE"

case "\$1" in
  start)
    if [[ -f "\$PIDFILE" ]] && kill -0 "\$(cat "\$PIDFILE")" 2>/dev/null; then
      echo "orbvis already running (pid \$(cat "\$PIDFILE"))"
      exit 0
    fi
    echo -n "Starting orbvis..."
    set -a; source "\$ENV_FILE"; set +a
    PORT="\${ORBVIS_PORT:-8420}"
    export LD_LIBRARY_PATH="\$OMD_ROOT/lib\${LD_LIBRARY_PATH:+:\$LD_LIBRARY_PATH}"
    cd "$ORBVIS_DIR/src"
    "\$VENV/bin/python3" -m alembic upgrade head >> "\$LOGFILE" 2>&1
    "\$VENV/bin/uvicorn" \$APP \\
      --host 127.0.0.1 --port "\$PORT" \\
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
        kill "\$PID" 2>/dev/null
        for _ in \$(seq 1 20); do
          kill -0 "\$PID" 2>/dev/null || break
          sleep 0.5
        done
        echo " OK"
      fi
      rm -f "\$PIDFILE"
    else
      echo "orbvis not running"
    fi
    ;;
  restart)
    \$0 stop
    \$0 start
    ;;
  status)
    if [[ -f "\$PIDFILE" ]] && kill -0 "\$(cat "\$PIDFILE")" 2>/dev/null; then
      echo "orbvis running (pid \$(cat "\$PIDFILE"))"
      exit 0
    else
      echo "orbvis not running"
      exit 1
    fi
    ;;
  *)
    echo "Usage: \$0 {start|stop|restart|status}"
    exit 1
    ;;
esac
EOF
quietly sudo chmod +x "$INIT_SCRIPT"
quietly sudo ln -sf "$INIT_SCRIPT" "$SITE_ROOT/etc/rc.d/85-orbvis"
ok "OrbVis registered as OMD service"

# 7. Checkmk GUI plugins
step "Installing Checkmk GUI plugins"
quietly sudo mkdir -p "$CMK_PLUGINS_DST"
quietly sudo cp -r "$CMK_PLUGINS_SRC/." "$CMK_PLUGINS_DST/"
quietly sudo chown -R "$SITE:$SITE" "$CMK_PLUGINS_DST"
quietly sudo -u "$SITE" "$PYTHON3" -m pip install --quiet -e "$CMK_PLUGINS_DST"
ok "Checkmk GUI plugins installed"

# 8. Ownership
step "Setting file permissions"
quietly sudo chown -R "$SITE:$SITE" "$ORBVIS_DIR"
ok "Permissions set"

# 9. Start services
step "Restarting Apache"
quietly sudo omd restart "$SITE" apache
ok "Apache restarted"

step "Starting OrbVis backend"
cd /tmp
quietly sudo -u "$SITE" omd restart orbvis
ok "OrbVis backend started"

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
HOST="$(hostname -f 2>/dev/null || hostname)"
echo ""
echo -e "${GREEN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "${GREEN}${BOLD}  OrbVis successfully installed!${RESET}"
echo -e "${GREEN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo ""
echo "  Open in browser:  https://$HOST$BASE_PATH/"
echo ""
echo "  Main menu:        OrbVis entry in the Checkmk navigation bar"
echo ""
echo "  To add the sidebar snapin:"
echo "  Edit sidebar → Add snapin → OrbVis Boards"
echo ""
echo "  Install log: $LOG_FILE"
echo ""
