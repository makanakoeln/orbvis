#!/bin/bash
# install_cmk.sh – Deploy/remove OrbVis in an OMD/cmk site
# Usage: ./install_cmk.sh <site-name> [install|remove]
# Run as a normal user; sudo is invoked automatically for privileged steps.
set -euo pipefail

SITE="${1:-}"
ACTION="${2:-install}"

if [[ -z "$SITE" ]] || [[ "$ACTION" != "install" && "$ACTION" != "remove" ]]; then
  echo "Usage: $0 <site-name> [install|remove]" >&2
  exit 1
fi

if [[ "$EUID" -eq 0 ]]; then
  echo "Error: run this script as a normal user, not as root." >&2
  exit 1
fi

SITE_ROOT="/omd/sites/$SITE"
if [[ ! -d "$SITE_ROOT" ]]; then
  echo "Error: OMD site '$SITE' not found (expected $SITE_ROOT)" >&2
  exit 1
fi

# Pre-authenticate sudo once so subsequent sudo calls don't re-prompt
echo "sudo credentials are needed for privileged operations."
sudo -v

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Paths inside the site
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
SNAPIN_DIR="$SITE_ROOT/local/share/check_mk/web/plugins/sidebar"
SNAPIN_FILE="$SNAPIN_DIR/orbvis_boards.py"
APACHE_CONF="$SITE_ROOT/etc/apache/conf.d/orbvis.conf"
INIT_SCRIPT="$SITE_ROOT/etc/init.d/orbvis"

# Check required tools
NPM="$(command -v npm 2>/dev/null || true)"
if [[ -z "$NPM" ]]; then
  echo "Error: npm not found. Install Node.js >= 18:" >&2
  echo "  sudo apt install nodejs npm" >&2
  exit 1
fi
NODE_MAJOR="$(node --version 2>/dev/null | sed 's/v\([0-9]*\).*/\1/')"
if [[ -z "$NODE_MAJOR" ]] || [[ "$NODE_MAJOR" -lt 18 ]]; then
  echo "Error: Node.js >= 18 required (found: $(node --version 2>/dev/null || echo 'none'))." >&2
  echo "  Install via: https://github.com/nodesource/distributions" >&2
  exit 1
fi

# Prefer the OMD site's own Python (correct permissions, correct version).
# Avoids issues where the system python3 is a wrapper (bazel, pyenv, conda, …)
# whose symlink targets are inaccessible to the site user.
if [[ -x "$SITE_ROOT/bin/python3" ]]; then
  PYTHON3="$SITE_ROOT/bin/python3"
else
  PYTHON3="$(command -v python3 2>/dev/null || true)"
  if [[ -z "$PYTHON3" ]]; then
    echo "Error: python3 not found. Install Python 3.12 or newer:" >&2
    echo "  sudo apt install python3.12 python3.12-venv" >&2
    exit 1
  fi
fi
echo "    Using Python: $PYTHON3"

# ---------------------------------------------------------------------------
# REMOVE
# ---------------------------------------------------------------------------
if [[ "$ACTION" == "remove" ]]; then
  echo "==> Removing OrbVis from cmk site '$SITE'..."

  echo "    Stopping backend..."
  sudo -u "$SITE" omd stop orbvis 2>/dev/null || true

  echo "    Removing files..."
  sudo rm -f  "$APACHE_CONF" "$INIT_SCRIPT" "$SITE_ROOT/etc/rc.d/85-orbvis" "$SNAPIN_FILE"
  sudo rm -rf "$HTDOCS_DIR" "$VENV_DIR" "$ORBVIS_DIR/src" "$DB_FILE" "$ENV_FILE" "$BACKENDS_FILE"
  # Maps are kept — remove manually if no longer needed

  echo "    Reloading Apache..."
  sudo omd reload "$SITE" apache

  echo ""
  echo "Done. OrbVis has been removed from site '$SITE'."
  echo "Board files were kept in: $BOARDS_DIR"
  echo "To also remove those, run: sudo rm -rf $BOARDS_DIR"
  exit 0
fi

# ---------------------------------------------------------------------------
# INSTALL
# ---------------------------------------------------------------------------
echo "==> Installing OrbVis into cmk site '$SITE'"
echo "    Site root:    $SITE_ROOT"
echo "    OrbVis dir:   $ORBVIS_DIR"
echo "    Backend port: $BACKEND_PORT"
echo "    Base path:    $BASE_PATH"
echo ""

# ---------------------------------------------------------------------------
# 1. Build frontend (runs as current user, no sudo needed)
# ---------------------------------------------------------------------------
echo "==> Building Vue frontend (base=$BASE_PATH/)..."
cd "$SCRIPT_DIR/frontend"
"$NPM" install --silent
"$NPM" run build -- --base="$BASE_PATH/"

echo "==> Deploying frontend to $HTDOCS_DIR..."
sudo rm -rf "$HTDOCS_DIR"
sudo mkdir -p "$HTDOCS_DIR"
sudo cp -r "$SCRIPT_DIR/frontend/dist/." "$HTDOCS_DIR/"

# ---------------------------------------------------------------------------
# 2. Create data directories
# ---------------------------------------------------------------------------
ICONS_DIR="$(dirname "$BOARDS_DIR")/icons"
sudo mkdir -p "$BOARDS_DIR" "$ICONS_DIR"

# ---------------------------------------------------------------------------
# 3. Python virtualenv + backend dependencies
# ---------------------------------------------------------------------------
echo "==> Setting up Python virtualenv..."
if sudo test -d "$VENV_DIR"; then
  echo "    Virtualenv already exists, skipping creation."
else
  # --copies: avoids symlinks into the original Python prefix (important when
  # python3 is a wrapper/bazel binary whose real path is user-specific).
  sudo "$PYTHON3" -m venv --copies "$VENV_DIR"
fi
echo "==> Installing backend dependencies..."
sudo "$VENV_DIR/bin/pip" install --quiet --upgrade pip
# Copy backend source into the site directory so the site user can import it
# without needing access to the developer's home directory.
sudo cp -r "$SCRIPT_DIR/backend/." "$ORBVIS_DIR/src/"
# Editable install: keeps __file__ pointing at $ORBVIS_DIR/src so that
# relative paths (alembic.ini, alembic/ migrations dir) resolve correctly.
sudo "$VENV_DIR/bin/pip" install --quiet -e "$ORBVIS_DIR/src"

# ---------------------------------------------------------------------------
# 4. .env configuration
# ---------------------------------------------------------------------------
echo "==> Writing $ENV_FILE..."
# Preserve secret_key if it already exists
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

# ---------------------------------------------------------------------------
# 5. backends.json
# ---------------------------------------------------------------------------
if sudo test -f "$BACKENDS_FILE"; then
  echo "    $BACKENDS_FILE already exists, skipping."
else
  echo "==> Writing $BACKENDS_FILE..."
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
fi

# ---------------------------------------------------------------------------
# 6. Apache configuration
# ---------------------------------------------------------------------------
echo "==> Writing Apache config: $APACHE_CONF..."
sudo tee "$APACHE_CONF" > /dev/null <<EOF
# OrbVis – static frontend + backend proxy
# Auto-generated by install_cmk.sh

# OMD ships its own Apache binary – load proxy modules from OMD's module path
<IfModule !mod_proxy.c>
    LoadModule proxy_module $SITE_ROOT/lib/apache/modules/mod_proxy.so
</IfModule>
<IfModule !mod_proxy_http.c>
    LoadModule proxy_http_module $SITE_ROOT/lib/apache/modules/mod_proxy_http.so
</IfModule>

Alias /$SITE/orbvis $HTDOCS_DIR

# OrbVis handles authentication itself via cmk session cookie SSO.
# AuthType None overrides OMD's auth.conf so the browser never sees a challenge.
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
    # mod_allowmethods (loaded by OMD) returns 405 for unlisted methods.
    # Override here to allow the full set of methods needed by the REST API.
    <IfModule mod_allowmethods.c>
        AllowMethods GET POST PUT PATCH DELETE OPTIONS HEAD
    </IfModule>
    ProxyPass        http://127.0.0.1:$BACKEND_PORT/api
    ProxyPassReverse http://127.0.0.1:$BACKEND_PORT/api
</Location>

# Static files served by the backend (uploaded icons and map backgrounds).
# These Location blocks take precedence over the Alias above.
<Location /$SITE/orbvis/icons>
    ProxyPass        http://127.0.0.1:$BACKEND_PORT/icons
    ProxyPassReverse http://127.0.0.1:$BACKEND_PORT/icons
</Location>

<Location /$SITE/orbvis/boards/backgrounds>
    ProxyPass        http://127.0.0.1:$BACKEND_PORT/boards/backgrounds
    ProxyPassReverse http://127.0.0.1:$BACKEND_PORT/boards/backgrounds
</Location>
EOF

# ---------------------------------------------------------------------------
# 7. OMD init script
# ---------------------------------------------------------------------------
echo "==> Writing OMD init script: $INIT_SCRIPT..."
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
      echo -n "Stopping orbvis (pid \$PID)..."
      kill "\$PID" 2>/dev/null && rm -f "\$PIDFILE"
      echo " OK"
    else
      echo "orbvis not running"
    fi
    ;;
  restart)
    \$0 stop
    sleep 1
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
sudo chmod +x "$INIT_SCRIPT"

# rc.d symlink – required for omd status/start/stop to recognise the service
RC_LINK="$SITE_ROOT/etc/rc.d/85-orbvis"
sudo ln -sf "$INIT_SCRIPT" "$RC_LINK"

# ---------------------------------------------------------------------------
# 8. cmk sidebar snapin
# ---------------------------------------------------------------------------
sudo mkdir -p "$SNAPIN_DIR"
echo "==> Writing sidebar snapin: $SNAPIN_FILE..."
sudo tee "$SNAPIN_FILE" > /dev/null <<'PYEOF'
# OrbVis sidebar snapin – shows all available OrbVis boards as links
# Auto-generated by install_cmk.sh

import os
import json
import pathlib
from typing import List, Tuple

from cmk.gui.htmllib.html import html
from cmk.gui.i18n import _
from cmk.gui.plugins.sidebar.utils import SidebarSnapin, snapin_registry
from cmk.gui.sidebar._snapin._helpers import footnotelinks

_BOARDS_DIR = pathlib.Path(os.environ.get("OMD_ROOT", "")) / "local" / "share" / "orbvis" / "boards"
_SITE = os.environ.get("OMD_SITE", "")
_BASE_URL = f"/{_SITE}/orbvis/#/boards"
_EDIT_URL = f"/{_SITE}/orbvis/#/"


def _get_maps() -> List[Tuple[str, str]]:
    results = []
    if not _BOARDS_DIR.is_dir():
        return results
    for p in sorted(_BOARDS_DIR.glob("*.json")):
        try:
            data = json.loads(p.read_text())
            name = data.get("name") or p.stem
            alias = data.get("alias") or name
            results.append((name, alias))
        except Exception:
            results.append((p.stem, p.stem))
    return results


@snapin_registry.register
class OrbVisBoardsSnapin(SidebarSnapin):
    @staticmethod
    def type_name() -> str:
        return "orbvis_boards"

    @classmethod
    def title(cls) -> str:
        return _("OrbVis Boards")

    @classmethod
    def description(cls) -> str:
        return _("Links to OrbVis monitoring boards")

    @classmethod
    def allowed_roles(cls):
        return ["admin", "user", "guest"]

    def show(self) -> None:
        maps = _get_maps()
        if not maps:
            html.p(_("No OrbVis boards found."))
        else:
            html.open_ul(class_="snapin_nagtree")
            for name, alias in maps:
                url = f"{_BASE_URL}/{name}"
                html.open_li()
                html.open_a(href=url, target="main", title=alias)
                html.icon("network_topology", title=None)
                html.write_text(f" {alias}")
                html.close_a()
                html.close_li()
            html.close_ul()

        footnotelinks([(_("Edit"), _EDIT_URL)])
PYEOF

# ---------------------------------------------------------------------------
# 9. Fix ownership
# ---------------------------------------------------------------------------
echo "==> Setting file ownership to site user '$SITE'..."
sudo chown -R "$SITE:$SITE" "$ORBVIS_DIR"

# ---------------------------------------------------------------------------
# 10. Reload Apache and start backend
# ---------------------------------------------------------------------------
echo "==> Reloading Apache..."
sudo omd reload "$SITE" apache

echo "==> Restarting OrbVis backend..."
# cd to a neutral directory before switching to the site user —
# omd restores the cwd after chdir() and the site user has no access to
# the developer's working directory (e.g. /home/…/frontend).
cd /tmp
sudo -u "$SITE" omd restart orbvis

HOST="$(hostname -f 2>/dev/null || hostname)"

echo ""
echo "Done! OrbVis is available at:"
echo "  https://$HOST/$SITE/orbvis/"
echo ""
echo "Add the 'OrbVis Boards' snapin via: Edit sidebar -> OrbVis Maps"
