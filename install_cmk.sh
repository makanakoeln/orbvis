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

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ORBVIS_DIR="$SITE_ROOT/local/share/orbvis"
HTDOCS_DIR="$ORBVIS_DIR/htdocs"
BOARDS_DIR="$ORBVIS_DIR/boards"
ENV_FILE="$ORBVIS_DIR/.env"
BACKENDS_FILE="$ORBVIS_DIR/backends.json"
DB_FILE="$ORBVIS_DIR/orbvis.db"
BACKEND_PORT=8420
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
NPM="$(command -v npm 2>/dev/null || true)"
[[ -z "$NPM" ]] && die "npm not found. Install Node.js >= 18:\n  sudo apt install nodejs npm"

NODE_MAJOR="$(node --version 2>/dev/null | sed 's/v\([0-9]*\).*/\1/')"
[[ -z "$NODE_MAJOR" || "$NODE_MAJOR" -lt 18 ]] && \
  die "Node.js >= 18 required (found: $(node --version 2>/dev/null || echo none))."

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
  quietly sudo rm -rf "$HTDOCS_DIR" "$VENV_DIR" "$ORBVIS_DIR/src" "$CMK_PLUGINS_DST" "$DB_FILE" "$ENV_FILE" "$BACKENDS_FILE"
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
echo "  URL:     https://$(hostname -f 2>/dev/null || hostname)$BASE_PATH/"
: > "$LOG_FILE"

# 1. Frontend
step "Building frontend"
cd "$SCRIPT_DIR/frontend"
quietly "$NPM" install
quietly "$NPM" run build -- --base="$BASE_PATH/"
quietly sudo rm -rf "$HTDOCS_DIR"
quietly sudo mkdir -p "$HTDOCS_DIR"
quietly sudo cp -r "$SCRIPT_DIR/frontend/dist/." "$HTDOCS_DIR/"
ok "Frontend built and deployed"

# 2. Data directories + demo boards
step "Setting up data directories"
IMAGES_DIR="$(dirname "$BOARDS_DIR")/images"
quietly sudo mkdir -p "$BOARDS_DIR/backgrounds" "$IMAGES_DIR"
NEW_BOARDS=0
for demo in "$SCRIPT_DIR/backend/boards/"demo*.json; do
  fname="$(basename "$demo")"
  if ! sudo test -f "$BOARDS_DIR/$fname"; then
    quietly sudo cp "$demo" "$BOARDS_DIR/$fname"
    (( NEW_BOARDS++ )) || true
  fi
done
if ! sudo test -f "$BOARDS_DIR/backgrounds/demo.svg"; then
  quietly sudo cp "$SCRIPT_DIR/backend/boards/backgrounds/demo.svg" "$BOARDS_DIR/backgrounds/demo.svg"
fi
[[ $NEW_BOARDS -gt 0 ]] && ok "Directories ready ($NEW_BOARDS demo board(s) installed)" \
                         || ok "Directories ready (demo boards already present)"

# 3. Python virtualenv + dependencies
step "Setting up Python environment"
if sudo test -d "$VENV_DIR"; then
  ok "Virtualenv already exists, skipping creation"
else
  quietly sudo "$PYTHON3" -m venv --copies "$VENV_DIR"
fi
step "Installing backend dependencies"
quietly sudo "$VENV_DIR/bin/pip" install --quiet --upgrade pip
quietly sudo cp -r "$SCRIPT_DIR/backend/." "$ORBVIS_DIR/src/"
quietly sudo "$VENV_DIR/bin/pip" install --quiet -e "$ORBVIS_DIR/src"
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
BACKENDS_FILE=$BACKENDS_FILE
DATABASE_URL=sqlite+aiosqlite:///$DB_FILE
SECRET_KEY=$SECRET_KEY
STATE_REFRESH_INTERVAL=15
CHECKMK_HTPASSWD=$SITE_ROOT/etc/htpasswd
CHECKMK_OMD_ROOT=$SITE_ROOT
CHECKMK_SITE=$SITE
EOF

if sudo test -f "$BACKENDS_FILE"; then
  ok "Configuration written (existing backends.json kept)"
else
  if sudo -u "$SITE" omd config show LIVEPROXYD 2>/dev/null | grep -qi "^on$"; then
    LIVESTATUS_SOCKET="$SITE_ROOT/tmp/run/liveproxyd/$SITE.sock"
  fi
  sudo tee "$BACKENDS_FILE" > /dev/null <<EOF
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

sudo tee "$APACHE_CONF" > /dev/null <<EOF
# OrbVis – static frontend + backend proxy
# Auto-generated by install_cmk.sh

<IfModule !mod_proxy.c>
    LoadModule proxy_module $APACHE_MODULES_DIR/mod_proxy.so
</IfModule>
<IfModule !mod_proxy_http.c>
    LoadModule proxy_http_module $APACHE_MODULES_DIR/mod_proxy_http.so
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
    <IfModule mod_allowmethods.c>
        AllowMethods GET POST PUT PATCH DELETE OPTIONS HEAD
    </IfModule>
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
sudo tee "$INIT_SCRIPT" > /dev/null <<EOF
#!/bin/bash
# OMD init script for OrbVis backend

PIDFILE="\$OMD_ROOT/tmp/run/orbvis.pid"
LOGFILE="\$OMD_ROOT/var/log/orbvis.log"
VENV="$VENV_DIR"
APP="app.main:app"
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
    cd "$ORBVIS_DIR/src"
    "\$VENV/bin/python3" -m alembic upgrade head >> "\$LOGFILE" 2>&1
    "\$VENV/bin/uvicorn" \$APP \\
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
