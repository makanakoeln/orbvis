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

# Dual-mode: when invoked via `sudo deploy-cmc.sh` (EUID=0, NOPASSWD path),
# run privileged commands directly. When invoked as a normal user, prefix
# privileged steps with sudo and authenticate once up front.
if [[ "$EUID" -eq 0 ]]; then
  INVOKER="${SUDO_USER:-$(logname 2>/dev/null || true)}"
  [[ -z "$INVOKER" || "$INVOKER" == "root" ]] && \
    die "Cannot determine invoking user (SUDO_USER unset). Run via 'sudo $0 ...' from a normal user shell."
  AS_ROOT=()
else
  AS_ROOT=("sudo")
fi
AS_SITE=("sudo" "-u" "$SITE")

SITE_ROOT="/omd/sites/$SITE"
[[ -d "$SITE_ROOT" ]] || die "OMD site '$SITE' not found."

# Detect CMK version from site symlink (e.g. ../../versions/2.4.0p24.cre → 2.4.0p24)
CMK_VERSION_RAW=$(readlink "$SITE_ROOT/version" 2>/dev/null || true)
CMK_VERSION=$(basename "${CMK_VERSION_RAW}" | sed 's/\.[a-z]*$//' 2>/dev/null || echo "unknown")

# ---------------------------------------------------------------------------
# Paths
#
# Layout (split between var/ and etc/ so the WATO replication snapshot, which
# pushes the whole local/ tree to every remote site, leaves OrbVis untouched):
#   etc/orbvis/        – admin-edited config (.env with SECRET_KEY etc.)
#   var/orbvis/        – everything else: boards, db, connections, venv,
#                        htdocs, backend source, plugin source
# Neither path is in cmk.gui.watolib.activate_changes.replication_paths.
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ORBVIS_DIR="$SITE_ROOT/var/orbvis"
ORBVIS_ETC_DIR="$SITE_ROOT/etc/orbvis"
LEGACY_DIR="$SITE_ROOT/local/share/orbvis"
HTDOCS_DIR="$ORBVIS_DIR/htdocs"
BOARDS_DIR="$ORBVIS_DIR/boards"
ENV_FILE="$ORBVIS_ETC_DIR/.env"
CONNECTIONS_FILE="$ORBVIS_DIR/connections.json"
DB_FILE="$ORBVIS_DIR/orbvis.db"
# Determine port: reuse existing from .env if present, else pick the lowest
# free port from 8420 upward. Skip ports already reserved by other OrbVis
# installs on this host (their .env may pin a port even while the site is
# stopped) as well as anything currently bound in the live socket table.
# Probe both the new (etc/orbvis/.env) and the legacy (local/share/orbvis/.env)
# locations so a pre-migration install still surfaces its reserved port.
BACKEND_PORT=""
for probe in "$ENV_FILE" "$LEGACY_DIR/.env"; do
  if [[ -z "$BACKEND_PORT" ]] && "${AS_ROOT[@]}" test -f "$probe" 2>/dev/null; then
    BACKEND_PORT=$("${AS_ROOT[@]}" grep -E '^ORBVIS_PORT=' "$probe" 2>/dev/null | head -1 | cut -d= -f2- || true)
  fi
done
if [[ -z "$BACKEND_PORT" ]]; then
  declare -A RESERVED_PORTS=()
  for envf in /omd/sites/*/etc/orbvis/.env /omd/sites/*/local/share/orbvis/.env; do
    [[ -f "$envf" && "$envf" != "$ENV_FILE" ]] || continue
    p=$("${AS_ROOT[@]}" grep -E '^ORBVIS_PORT=' "$envf" 2>/dev/null | head -1 | cut -d= -f2- || true)
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
if [[ ! -d "$SCRIPT_DIR/htdocs" && "${ORBVIS_SKIP_BUILD:-0}" != "1" ]]; then
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
[[ "$EUID" -ne 0 ]] && sudo -v

# ---------------------------------------------------------------------------
# REMOVE
# ---------------------------------------------------------------------------
if [[ "$ACTION" == "remove" ]]; then
  header "Removing OrbVis from site '$SITE'"
  : > "$LOG_FILE"

  step "Stopping OrbVis backend"
  quietly "${AS_SITE[@]}" omd stop orbvis 2>/dev/null || true
  ok "Backend stopped"

  step "Removing files"
  quietly "${AS_ROOT[@]}" rm -f "$APACHE_CONF" "$INIT_SCRIPT" "$SITE_ROOT/etc/rc.d/85-orbvis"
  quietly "${AS_SITE[@]}" "$PYTHON3" -m pip uninstall -y orbvis-cmk 2>/dev/null || true
  quietly "${AS_ROOT[@]}" rm -rf "$HTDOCS_DIR" "$VENV_DIR" "$ORBVIS_DIR/src" "$CMK_PLUGINS_DST" "$DB_FILE" "$ENV_FILE" "$CONNECTIONS_FILE"
  # Bridge plugins live in local/ and are part of the WATO replication snapshot;
  # leaving them behind would propagate broken links to every remote on the
  # next Activate Changes.
  for orbvis_plugin in \
      "$SITE_ROOT/local/lib/python3/cmk/gui/plugins/sidebar/orbvis_boards.py" \
      "$SITE_ROOT/local/lib/python3/cmk/gui/plugins/wato/orbvis_menu.py" \
      "$SITE_ROOT/local/lib/python3/cmk/gui/plugins/wato/orbvis_permissions.py"; do
    quietly "${AS_ROOT[@]}" rm -f "$orbvis_plugin"
  done
  # Sweep up any leftovers from pre-migration installs under local/share/orbvis/.
  quietly "${AS_ROOT[@]}" rm -rf \
    "$LEGACY_DIR/htdocs" "$LEGACY_DIR/venv" "$LEGACY_DIR/src" \
    "$LEGACY_DIR/cmk_plugins" "$LEGACY_DIR/orbvis.db" \
    "$LEGACY_DIR/.env" "$LEGACY_DIR/connections.json"
  ok "Files removed"

  step "Reloading Apache"
  quietly "${AS_ROOT[@]}" omd reload "$SITE" apache
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

# Ensure target directories exist before any step writes into them.
quietly "${AS_ROOT[@]}" mkdir -p "$ORBVIS_DIR" "$ORBVIS_ETC_DIR"

# 0. Migrate data from legacy local/share/orbvis/ to var/orbvis/ + etc/orbvis/
#
# Up to v0.x OrbVis lived entirely under $OMD_ROOT/local/share/orbvis/. That
# directory is part of cmk.gui.watolib.activate_changes.replication_paths
# (ident="local"), so every WATO "Activate Changes" pushed boards, db, venv
# and htdocs to all remote sites. Move user data to var/orbvis/ (and the
# admin .env to etc/orbvis/) where the snapshot doesn't reach. Idempotent.
if "${AS_ROOT[@]}" test -d "$LEGACY_DIR" 2>/dev/null; then
  MIGRATED=0
  step "Migrating data from legacy local/share/orbvis/"

  # User data: boards (incl. backgrounds), images, db, connections, settings.
  # ``backends.json`` is the pre-rename predecessor of ``connections.json``;
  # the backend's connection_service still recognises and renames it on
  # startup, so we just move it along.
  for sub in boards images orbvis.db connections.json backends.json settings.json; do
    if "${AS_ROOT[@]}" test -e "$LEGACY_DIR/$sub" \
       && ! "${AS_ROOT[@]}" test -e "$ORBVIS_DIR/$sub"; then
      quietly "${AS_ROOT[@]}" mv "$LEGACY_DIR/$sub" "$ORBVIS_DIR/$sub"
      MIGRATED=1
    fi
  done

  # .env goes to etc/orbvis/. Path entries inside .env get rewritten below in
  # step 4 since BOARDS_DIR / DATABASE_URL / CONNECTIONS_FILE all changed.
  if "${AS_ROOT[@]}" test -f "$LEGACY_DIR/.env" \
     && ! "${AS_ROOT[@]}" test -f "$ENV_FILE"; then
    quietly "${AS_ROOT[@]}" mv "$LEGACY_DIR/.env" "$ENV_FILE"
    MIGRATED=1
  fi

  # Disposable artefacts: drop the legacy venv (shebangs point at the old
  # path) and htdocs/src/cmk_plugins (will be re-deployed below). The
  # editable pip install registered in the site-python's easy-install.pth
  # still points at the legacy cmk_plugins path; uninstall it so the
  # re-install in step 7 picks up the new location.
  if "${AS_ROOT[@]}" test -d "$LEGACY_DIR/venv"; then
    quietly "${AS_SITE[@]}" "$LEGACY_DIR/venv/bin/python3" -m pip uninstall -y orbvis-cmk 2>/dev/null || true
    quietly "${AS_SITE[@]}" "$PYTHON3" -m pip uninstall -y orbvis-cmk 2>/dev/null || true
  fi
  quietly "${AS_ROOT[@]}" rm -rf \
    "$LEGACY_DIR/htdocs" "$LEGACY_DIR/venv" "$LEGACY_DIR/src" \
    "$LEGACY_DIR/cmk_plugins" "$LEGACY_DIR/VERSION" "$LEGACY_DIR/CHANGELOG.md"

  # User-data leftovers that didn't migrate because the destination already
  # existed (e.g. settings.json written after a partial run). The destination
  # is canonical; drop the legacy copy so it can't leak via WATO replication.
  for sub in boards images orbvis.db connections.json backends.json settings.json .env; do
    if "${AS_ROOT[@]}" test -e "$LEGACY_DIR/$sub" \
       && "${AS_ROOT[@]}" test -e "$ORBVIS_DIR/$sub"; then
      quietly "${AS_ROOT[@]}" rm -rf "$LEGACY_DIR/$sub"
    fi
  done

  # Stop the OrbVis backend (if it's running on the legacy paths) so it
  # doesn't keep file handles open while step 3/4 rebuilds the venv.
  quietly "${AS_SITE[@]}" omd stop orbvis 2>/dev/null || true

  # If nothing meaningful is left in $LEGACY_DIR, remove it entirely so the
  # next replication snapshot has nothing to delete on this site.
  if "${AS_ROOT[@]}" test -d "$LEGACY_DIR" \
     && [[ -z "$("${AS_ROOT[@]}" ls -A "$LEGACY_DIR" 2>/dev/null || echo x)" ]]; then
    quietly "${AS_ROOT[@]}" rmdir "$LEGACY_DIR"
  fi

  if [[ "$MIGRATED" == "1" ]]; then
    ok "Migrated boards/db/connections/.env to var/orbvis + etc/orbvis"
  else
    ok "Legacy directory cleaned (no user data to migrate)"
  fi
fi

# 1. Frontend
if [[ -d "$SCRIPT_DIR/htdocs" ]]; then
  step "Deploying pre-built frontend"
  quietly "${AS_ROOT[@]}" rm -rf "$HTDOCS_DIR"
  quietly "${AS_ROOT[@]}" mkdir -p "$HTDOCS_DIR"
  quietly "${AS_ROOT[@]}" cp -r "$SCRIPT_DIR/htdocs/." "$HTDOCS_DIR/"
  ok "Frontend deployed"
elif [[ "${ORBVIS_SKIP_BUILD:-0}" == "1" && -d "$SCRIPT_DIR/frontend/dist" ]]; then
  step "Deploying pre-built frontend dist"
  quietly "${AS_ROOT[@]}" rm -rf "$HTDOCS_DIR"
  quietly "${AS_ROOT[@]}" mkdir -p "$HTDOCS_DIR"
  quietly "${AS_ROOT[@]}" cp -r "$SCRIPT_DIR/frontend/dist/." "$HTDOCS_DIR/"
  ok "Frontend deployed (pre-built)"
else
  step "Building frontend"
  cd "$SCRIPT_DIR/frontend"
  quietly "$NPM" install
  quietly "$NPM" run build -- --base="$BASE_PATH/"
  quietly "${AS_ROOT[@]}" rm -rf "$HTDOCS_DIR"
  quietly "${AS_ROOT[@]}" mkdir -p "$HTDOCS_DIR"
  quietly "${AS_ROOT[@]}" cp -r "$SCRIPT_DIR/frontend/dist/." "$HTDOCS_DIR/"
  ok "Frontend built and deployed"
fi

# 2. Data directories + demo boards
step "Setting up data directories"
IMAGES_DIR="$(dirname "$BOARDS_DIR")/images"
quietly "${AS_ROOT[@]}" mkdir -p "$BOARDS_DIR/backgrounds" "$IMAGES_DIR"
# Only seed demo boards on a truly fresh install (no existing *.json in BOARDS_DIR)
if compgen -G "$BOARDS_DIR/*.json" > /dev/null; then
  ok "Directories ready (existing boards detected, skipping demo seed)"
else
  NEW_BOARDS=0
  for demo in "$SCRIPT_DIR/backend/app/_seed_boards/"demo*.json; do
    quietly "${AS_ROOT[@]}" cp "$demo" "$BOARDS_DIR/$(basename "$demo")"
    (( NEW_BOARDS++ )) || true
  done
  if ! "${AS_ROOT[@]}" test -f "$BOARDS_DIR/backgrounds/demo.svg"; then
    quietly "${AS_ROOT[@]}" cp "$SCRIPT_DIR/backend/app/_seed_boards/backgrounds/demo.svg" "$BOARDS_DIR/backgrounds/demo.svg"
  fi
  ok "Directories ready ($NEW_BOARDS demo board(s) installed)"
fi

# 3. Python virtualenv + dependencies
step "Setting up Python environment"
if "${AS_ROOT[@]}" test -d "$VENV_DIR"; then
  ok "Virtualenv already exists, skipping creation"
else
  # --system-site-packages lets OrbVis import cmk.rulesets.v1 (and other
  # cmk-plugin-apis modules) directly from the OMD site, which is the
  # source of truth for FormSpec types. See feedback_prefer_cmk_over_own.
  quietly "${AS_ROOT[@]}" "$PYTHON3" -m venv --symlinks --system-site-packages "$VENV_DIR"
fi
# Ensure venv python3 is a symlink so the OMD Python's RPATH is preserved.
# When venv copies the binary instead of symlinking, libpython3.13 can't be
# found at runtime because the relative RPATH no longer resolves correctly.
if [[ ! -L "$VENV_DIR/bin/python3" ]]; then
  quietly "${AS_ROOT[@]}" ln -sf "$PYTHON3" "$VENV_DIR/bin/python3"
fi
if ! "${AS_ROOT[@]}" test -f "$VENV_DIR/bin/pip"; then
  # CMK 2.5+ builds Python without ensurepip wheel; bootstrap pip from site
  quietly "${AS_ROOT[@]}" "$SITE_ROOT/bin/pip3" install --prefix="$VENV_DIR" pip \
    || die "Cannot install pip into virtualenv (tried $SITE_ROOT/bin/pip3)."
fi
step "Installing backend dependencies"
quietly "${AS_ROOT[@]}" "$VENV_DIR/bin/pip" install --quiet --upgrade pip
# rsync rather than cp -r so dev artefacts (backends.json, connections.json,
# *.db, boards/) from the source checkout never leak into the installed copy.
quietly "${AS_ROOT[@]}" rsync -a --delete \
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
quietly "${AS_ROOT[@]}" cp "$SCRIPT_DIR/VERSION" "$ORBVIS_DIR/VERSION"
quietly "${AS_ROOT[@]}" cp "$SCRIPT_DIR/CHANGELOG.md" "$ORBVIS_DIR/CHANGELOG.md"
quietly "${AS_ROOT[@]}" "$VENV_DIR/bin/pip" install --quiet -e "$ORBVIS_DIR/src"
# Clean up dev artefacts that earlier installs may have left behind in src/.
quietly "${AS_ROOT[@]}" rm -f "$ORBVIS_DIR/src/backends.json" "$ORBVIS_DIR/src/connections.json"
ok "Backend dependencies installed"

# 4. Configuration
step "Writing configuration"
EXISTING_SECRET=""
if "${AS_ROOT[@]}" test -f "$ENV_FILE"; then
  EXISTING_SECRET=$("${AS_ROOT[@]}" grep -E '^SECRET_KEY=' "$ENV_FILE" | head -1 | cut -d= -f2- || true)
fi
SECRET_KEY="${EXISTING_SECRET:-$("$PYTHON3" -c 'import secrets; print(secrets.token_hex(32))')}"

"${AS_ROOT[@]}" tee "$ENV_FILE" > /dev/null <<EOF
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

if "${AS_ROOT[@]}" test -f "$CONNECTIONS_FILE"; then
  ok "Configuration written (existing connections.json kept)"
else
  "${AS_ROOT[@]}" tee "$CONNECTIONS_FILE" > /dev/null <<EOF
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

"${AS_ROOT[@]}" tee "$APACHE_CONF" > /dev/null <<EOF
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
"${AS_ROOT[@]}" tee "$INIT_SCRIPT" > /dev/null <<EOF
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
    # Invoke uvicorn through the venv python: when OMD's site-python
    # already provides the uvicorn module (cmk-agent-receiver pulls it
    # in), \`pip install -e\` skips dropping the \`uvicorn\` console
    # script into the venv's bin/, so calling the binary directly
    # would fail with "No such file or directory".
    "\$VENV/bin/python3" -m uvicorn \$APP \\
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
quietly "${AS_ROOT[@]}" chmod +x "$INIT_SCRIPT"
quietly "${AS_ROOT[@]}" ln -sf "$INIT_SCRIPT" "$SITE_ROOT/etc/rc.d/85-orbvis"
ok "OrbVis registered as OMD service"

# 7. Checkmk GUI plugins
#
# Bridge plugins are KB-sized and live under ``local/lib/python3/cmk/gui/plugins``
# on purpose: that path *is* in cmk.gui.watolib.activate_changes.replication_paths
# (ident="local"), so a WATO Activate Changes propagates them from the master
# to every remote. The plugins themselves are auto-detecting — they check
# ``etc/apache/conf.d/orbvis.conf`` (outside replication) and render
# "OrbVis is not installed on this site" when the host doesn't run a local
# backend, so the propagated copy is harmless on those remotes.
#
# An earlier iteration installed them via pip-editable into ``var/orbvis/``,
# which kept the legacy duplicate-registration issue away but also stopped the
# WATO sync from picking them up — broken in distributed setups. The
# direct-copy path below is the documented design (see 2026-05-12 session
# notes / docs/architecture.md).
step "Installing Checkmk GUI plugins"
# Remove the old pip-editable install, if present. Repeated runs of this
# script must not leave both the new direct copy AND the editable copy in
# place — that's the duplicate-registration trap. Uninstall ``orbvis-cmk``
# best-effort.
quietly "${AS_SITE[@]}" "$PYTHON3" -m pip uninstall -y orbvis-cmk 2>/dev/null || true
quietly "${AS_ROOT[@]}" rm -rf "$CMK_PLUGINS_DST"
for plugin_relpath in \
    "lib/python3/cmk/gui/plugins/sidebar/orbvis_boards.py" \
    "lib/python3/cmk/gui/plugins/wato/orbvis_menu.py" \
    "lib/python3/cmk/gui/plugins/wato/orbvis_permissions.py"; do
  src="$CMK_PLUGINS_SRC/${plugin_relpath#lib/python3/}"
  dst="$SITE_ROOT/local/$plugin_relpath"
  quietly "${AS_ROOT[@]}" mkdir -p "$(dirname "$dst")"
  quietly "${AS_ROOT[@]}" cp "$src" "$dst"
done
quietly "${AS_ROOT[@]}" chown -R "$SITE:$SITE" "$SITE_ROOT/local/lib/python3/cmk/gui/plugins"
ok "Checkmk GUI plugins installed (in local/lib/, propagated via WATO sync)"

# 8. Ownership
step "Setting file permissions"
quietly "${AS_ROOT[@]}" chown -R "$SITE:$SITE" "$ORBVIS_DIR" "$ORBVIS_ETC_DIR"
quietly "${AS_ROOT[@]}" chmod 600 "$ENV_FILE"
ok "Permissions set"

# 9. Start services
step "Restarting Apache"
quietly "${AS_ROOT[@]}" omd restart "$SITE" apache
ok "Apache restarted"

step "Starting OrbVis backend"
cd /tmp
quietly "${AS_SITE[@]}" omd restart orbvis
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
