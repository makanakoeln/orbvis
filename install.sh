#!/bin/bash
# install.sh – Standalone install/remove of OrbVis (without Checkmk/OMD)
#
# Usage: ./install.sh [install|remove]
#
# What this script does:
#   - Installs OrbVis to /opt/orbvis
#   - Creates a system user 'orbvis'
#   - Sets up a Python virtualenv and installs the backend
#   - Builds the Vue frontend
#   - Creates a systemd service for the backend (port 8420)
#   - Configures nginx or apache2 as a reverse proxy (if installed)
#
# Requirements: python3 (>=3.12), npm, systemd, sudo
# Optional:     nginx or apache2 (for serving on port 80)
set -euo pipefail

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

ACTION="${1:-install}"

if [[ "$ACTION" != "install" && "$ACTION" != "remove" ]]; then
  echo "Usage: $0 [install|remove]" >&2
  exit 1
fi

if [[ "$EUID" -eq 0 ]]; then
  echo "Error: run this script as a normal user, not as root." >&2
  exit 1
fi

echo "sudo credentials are needed for privileged operations."
sudo -v

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

INSTALL_DIR="/opt/orbvis"
HTDOCS_DIR="$INSTALL_DIR/htdocs"
BOARDS_DIR="$INSTALL_DIR/boards"
ENV_FILE="$INSTALL_DIR/.env"
BACKENDS_FILE="$INSTALL_DIR/backends.json"
DB_FILE="$INSTALL_DIR/orbvis.db"
VENV_DIR="$INSTALL_DIR/venv"
BACKEND_PORT=8420
BASE_PATH="/orbvis"
SERVICE_USER="orbvis"
SYSTEMD_UNIT="/etc/systemd/system/orbvis.service"
if [[ "$OS_FAMILY" == "debian" ]]; then
  NGINX_CONF="/etc/nginx/sites-available/orbvis"
  NGINX_ENABLED="/etc/nginx/sites-enabled/orbvis"
  APACHE_CONF="/etc/apache2/sites-available/orbvis.conf"
else
  NGINX_CONF="/etc/nginx/conf.d/orbvis.conf"
  NGINX_ENABLED=""
  APACHE_CONF="/etc/httpd/conf.d/orbvis.conf"
fi

PYTHON3="$(command -v python3 2>/dev/null || true)"
NPM="$(command -v npm 2>/dev/null || true)"
PREBUILT_FRONTEND=false
[[ -d "$SCRIPT_DIR/htdocs" ]] && PREBUILT_FRONTEND=true
NGINX="$(command -v nginx 2>/dev/null || true)"
APACHE2="$(command -v apache2 2>/dev/null || command -v httpd 2>/dev/null || true)"
NOLOGIN="$(command -v nologin 2>/dev/null || echo /sbin/nologin)"

# ---------------------------------------------------------------------------
# REMOVE
# ---------------------------------------------------------------------------
if [[ "$ACTION" == "remove" ]]; then
  echo "==> Stopping and removing OrbVis..."

  sudo systemctl stop orbvis 2>/dev/null || true
  sudo systemctl disable orbvis 2>/dev/null || true
  sudo rm -f "$SYSTEMD_UNIT"
  sudo systemctl daemon-reload

  if [[ -L "$NGINX_ENABLED" ]]; then
    sudo rm -f "$NGINX_ENABLED"
    if sudo nginx -t 2>/dev/null; then sudo systemctl reload nginx; fi
  fi
  sudo rm -f "$NGINX_CONF"

  if [[ -f "$APACHE_CONF" ]]; then
    if [[ "$OS_FAMILY" == "debian" ]]; then
      sudo a2dissite orbvis 2>/dev/null || true
      sudo systemctl reload apache2 2>/dev/null || true
    else
      sudo systemctl reload httpd 2>/dev/null || true
    fi
    sudo rm -f "$APACHE_CONF"
  fi

  sudo rm -rf "$HTDOCS_DIR" "$VENV_DIR"
  # Keep boards/, .env, backends.json, orbvis.db – user data

  echo ""
  echo "Done. OrbVis has been removed."
  echo "Map data, database and config files were kept in: $INSTALL_DIR"
  echo "To also remove those, run: sudo rm -rf $INSTALL_DIR"
  exit 0
fi

# ---------------------------------------------------------------------------
# Pre-flight checks
# ---------------------------------------------------------------------------
if [[ -z "$PYTHON3" ]]; then
  echo "Error: python3 not found. Install Python 3.12 or newer:" >&2
  case "$OS_FAMILY" in
    rhel) echo "  sudo dnf install python3.12" >&2 ;;
    suse) echo "  sudo zypper install python312" >&2 ;;
    *)    echo "  sudo apt install python3.12 python3.12-venv" >&2 ;;
  esac
  exit 1
fi
if [[ "$PREBUILT_FRONTEND" == "false" && -z "$NPM" ]]; then
  echo "Error: npm not found. Install Node.js 18 or newer:" >&2
  case "$OS_FAMILY" in
    rhel) echo "  sudo dnf module enable nodejs:20 && sudo dnf install nodejs" >&2 ;;
    suse) echo "  sudo zypper install nodejs20" >&2 ;;
    *)    echo "  sudo apt install nodejs npm" >&2 ;;
  esac
  exit 1
fi

PYTHON_VERSION=$("$PYTHON3" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PYTHON_MINOR=$("$PYTHON3" -c 'import sys; print(sys.version_info.minor)')
if [[ "$("$PYTHON3" -c 'import sys; print(sys.version_info.major)')" -lt 3 ]] || [[ "$PYTHON_MINOR" -lt 12 ]]; then
  echo "Error: Python 3.12 or newer is required (found $PYTHON_VERSION)." >&2
  case "$OS_FAMILY" in
    rhel) echo "  sudo dnf install python3.12" >&2 ;;
    suse) echo "  sudo zypper install python312" >&2 ;;
    *)    echo "  sudo apt install python3.12 python3.12-venv" >&2 ;;
  esac
  exit 1
fi

# ---------------------------------------------------------------------------
# INSTALL
# ---------------------------------------------------------------------------
echo "==> Installing OrbVis (standalone)"
echo "    Install dir:  $INSTALL_DIR"
echo "    Backend port: $BACKEND_PORT"
echo "    Base path:    $BASE_PATH"
if [[ -n "$NGINX" ]]; then
  echo "    Web server:   nginx found – will configure reverse proxy"
elif [[ -n "$APACHE2" ]]; then
  echo "    Web server:   apache2/httpd found – will configure reverse proxy"
else
  echo "    Web server:   none found – backend will be accessible directly on port $BACKEND_PORT"
fi
echo ""

# ---------------------------------------------------------------------------
# 1. System user
# ---------------------------------------------------------------------------
if ! id "$SERVICE_USER" &>/dev/null; then
  echo "==> Creating system user '$SERVICE_USER'..."
  sudo useradd --system --no-create-home --shell "$NOLOGIN" "$SERVICE_USER"
fi

# ---------------------------------------------------------------------------
# 2. Install directory
# ---------------------------------------------------------------------------
IMAGES_DIR="$INSTALL_DIR/images"
sudo mkdir -p "$INSTALL_DIR" "$BOARDS_DIR" "$IMAGES_DIR"
sudo chown "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR" "$BOARDS_DIR" "$IMAGES_DIR"

# ---------------------------------------------------------------------------
# 3. Build/deploy frontend
# ---------------------------------------------------------------------------
if [[ "$PREBUILT_FRONTEND" == "true" ]]; then
  echo "==> Using pre-built frontend (already at $HTDOCS_DIR)"
  # $SCRIPT_DIR/htdocs == $HTDOCS_DIR when installed from package — nothing to copy
  sudo chown -R "$SERVICE_USER:$SERVICE_USER" "$HTDOCS_DIR"
else
  echo "==> Building Vue frontend (base=$BASE_PATH/)..."
  cd "$SCRIPT_DIR/frontend"
  "$NPM" install --silent
  "$NPM" run build -- --base="$BASE_PATH/"

  echo "==> Deploying frontend to $HTDOCS_DIR..."
  sudo rm -rf "$HTDOCS_DIR"
  sudo mkdir -p "$HTDOCS_DIR"
  sudo cp -r "$SCRIPT_DIR/frontend/dist/." "$HTDOCS_DIR/"
  sudo chown -R "$SERVICE_USER:$SERVICE_USER" "$HTDOCS_DIR"
fi

# ---------------------------------------------------------------------------
# 4. Python virtualenv + backend
# ---------------------------------------------------------------------------
echo "==> Setting up Python virtualenv..."
if [[ ! -d "$VENV_DIR" ]]; then
  sudo "$PYTHON3" -m venv "$VENV_DIR"
  sudo chown -R "$SERVICE_USER:$SERVICE_USER" "$VENV_DIR"
fi
echo "==> Installing backend dependencies..."
sudo "$VENV_DIR/bin/pip" install --quiet --upgrade pip
sudo "$VENV_DIR/bin/pip" install --quiet -e "$SCRIPT_DIR/backend"

# ---------------------------------------------------------------------------
# 5. .env configuration
# ---------------------------------------------------------------------------
if [[ ! -f "$ENV_FILE" ]]; then
  echo "==> Writing $ENV_FILE..."
  SECRET_KEY="$("$PYTHON3" -c 'import secrets; print(secrets.token_hex(32))')"
  sudo tee "$ENV_FILE" > /dev/null <<EOF
BOARDS_DIR=$BOARDS_DIR
BACKENDS_FILE=$BACKENDS_FILE
DATABASE_URL=sqlite+aiosqlite:///$DB_FILE
SECRET_KEY=$SECRET_KEY
STATE_REFRESH_INTERVAL=15
ALLOWED_ORIGINS=["http://localhost","http://localhost:80"]
EOF
  sudo chown "$SERVICE_USER:$SERVICE_USER" "$ENV_FILE"
  sudo chmod 600 "$ENV_FILE"
else
  echo "    $ENV_FILE already exists, skipping."
fi

# ---------------------------------------------------------------------------
# 6. backends.json
# ---------------------------------------------------------------------------
if [[ ! -f "$BACKENDS_FILE" ]]; then
  echo "==> Writing $BACKENDS_FILE..."
  sudo tee "$BACKENDS_FILE" > /dev/null <<'EOF'
[
  {
    "id": "live_1",
    "type": "livestatus",
    "label": "Monitoring",
    "socket_path": "/var/run/nagios/rw/live"
  }
]
EOF
  sudo chown "$SERVICE_USER:$SERVICE_USER" "$BACKENDS_FILE"
else
  echo "    $BACKENDS_FILE already exists, skipping."
fi

# ---------------------------------------------------------------------------
# 7. systemd service
# ---------------------------------------------------------------------------
echo "==> Writing systemd unit: $SYSTEMD_UNIT..."
sudo tee "$SYSTEMD_UNIT" > /dev/null <<EOF
[Unit]
Description=OrbVis monitoring visualization backend
After=network.target

[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_USER
WorkingDirectory=$INSTALL_DIR
EnvironmentFile=$ENV_FILE
ExecStart=$VENV_DIR/bin/uvicorn app.main:app \\
    --host 127.0.0.1 \\
    --port $BACKEND_PORT \\
    --log-level warning
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable orbvis
sudo systemctl restart orbvis

# ---------------------------------------------------------------------------
# 8. Web server configuration (nginx preferred, apache2 as fallback)
# ---------------------------------------------------------------------------
WEB_OK=false

if [[ -n "$NGINX" ]]; then
  echo "==> Writing nginx config: $NGINX_CONF..."
  sudo tee "$NGINX_CONF" > /dev/null <<EOF
# OrbVis – static frontend + API reverse proxy
# Auto-generated by install.sh

server {
    listen 80 default_server;
    server_name _;

    # Vue frontend
    location $BASE_PATH/ {
        alias $HTDOCS_DIR/;
        try_files \$uri \$uri/ @orbvis_fallback;
    }
    location @orbvis_fallback {
        rewrite ^ $BASE_PATH/index.html last;
    }

    # Proxy API and WebSocket to the uvicorn backend
    location $BASE_PATH/api/ {
        proxy_pass         http://127.0.0.1:$BACKEND_PORT/api/;
        proxy_http_version 1.1;
        proxy_set_header   Upgrade \$http_upgrade;
        proxy_set_header   Connection "upgrade";
        proxy_set_header   Host \$host;
        proxy_set_header   X-Real-IP \$remote_addr;
        proxy_read_timeout 3600;
    }

    # Uploaded images and built-in image set (served directly for performance)
    location $BASE_PATH/images/ {
        alias $INSTALL_DIR/images/;
        expires 1h;
        add_header Cache-Control "public";
    }

    # Background images uploaded via the API
    location $BASE_PATH/boards/backgrounds/ {
        alias $BOARDS_DIR/backgrounds/;
        expires 1h;
        add_header Cache-Control "public";
    }
}
EOF

  if [[ -n "$NGINX_ENABLED" ]]; then
    sudo ln -sf "$NGINX_CONF" "$NGINX_ENABLED"
  fi
  if sudo nginx -t; then
    sudo systemctl reload nginx
    WEB_OK=true
  else
    echo "Warning: nginx config test failed – check $NGINX_CONF manually." >&2
  fi

elif [[ -n "$APACHE2" ]]; then
  echo "==> Writing apache config: $APACHE_CONF..."
  sudo tee "$APACHE_CONF" > /dev/null <<EOF
# OrbVis – static frontend + API reverse proxy
# Auto-generated by install.sh

Alias $BASE_PATH $HTDOCS_DIR

<Directory $HTDOCS_DIR>
    Options -Indexes +FollowSymLinks
    AllowOverride None
    Require all granted
    FallbackResource $BASE_PATH/index.html
</Directory>

# WebSocket upgrade must be handled before the plain HTTP proxy
RewriteEngine On
RewriteCond %{HTTP:Upgrade} websocket [NC]
RewriteRule ^$BASE_PATH/api/(.*) ws://127.0.0.1:$BACKEND_PORT/api/\$1 [P,L]

<Location $BASE_PATH/api/>
    ProxyPass        http://127.0.0.1:$BACKEND_PORT/api/
    ProxyPassReverse http://127.0.0.1:$BACKEND_PORT/api/
</Location>

# Uploaded images and built-in image set (served directly)
Alias $BASE_PATH/images/ $INSTALL_DIR/images/
<Directory $INSTALL_DIR/images/>
    Options -Indexes
    Require all granted
</Directory>

# Background images uploaded via the API (served directly)
Alias $BASE_PATH/boards/backgrounds/ $BOARDS_DIR/backgrounds/
<Directory $BOARDS_DIR/backgrounds/>
    Options -Indexes
    Require all granted
</Directory>
EOF

  if [[ "$OS_FAMILY" == "debian" ]]; then
    sudo a2enmod proxy proxy_http proxy_wstunnel rewrite 2>/dev/null
    sudo a2ensite orbvis
    if sudo apache2ctl configtest; then
      sudo systemctl reload apache2
      WEB_OK=true
    else
      echo "Warning: apache2 config test failed – check $APACHE_CONF manually." >&2
    fi
  else
    if sudo apachectl configtest; then
      sudo systemctl reload httpd
      WEB_OK=true
    else
      echo "Warning: httpd config test failed – check $APACHE_CONF manually." >&2
    fi
  fi
fi

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
HOST="$(hostname -f 2>/dev/null || hostname)"

echo ""
echo "Done! OrbVis is running."
echo ""
if [[ "$WEB_OK" == "true" ]]; then
  echo "  Frontend:  http://$HOST$BASE_PATH/"
  echo "  API docs:  http://$HOST$BASE_PATH/api/docs"
else
  echo "  Backend:   http://$HOST:$BACKEND_PORT/api/docs"
  echo ""
  echo "  No web server was configured. To serve the frontend, install nginx and re-run:"
  case "$OS_FAMILY" in
    rhel) echo "    sudo dnf install nginx" ;;
    suse) echo "    sudo zypper install nginx" ;;
    *)    echo "    sudo apt install nginx" ;;
  esac
  echo "  Or serve $HTDOCS_DIR manually and proxy $BASE_PATH/api/ to port $BACKEND_PORT."
fi
echo ""
echo "  The default admin password is printed in the backend log:"
echo "    sudo journalctl -u orbvis --no-pager | grep 'Default admin'"
echo ""
echo "  Edit $BACKENDS_FILE to point to your monitoring socket."
