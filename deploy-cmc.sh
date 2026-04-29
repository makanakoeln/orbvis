#!/bin/bash
# Deploys OrbVis (frontend + backend) to the CMC OMD site.
# Run via: sudo ./deploy-cmc.sh (or `npm run deploy:cmc` from frontend/)
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SITE_DIR=/omd/sites/CMC/local/share/orbvis
OUTER_APACHE_CONF=/etc/apache2/conf-available/aaa-orbvis-ws.conf
OUTER_APACHE_ENABLED=/etc/apache2/conf-enabled/aaa-orbvis-ws.conf

# Frontend (only if dist/ exists)
if [[ -d "$REPO/frontend/dist" ]]; then
  rsync -a --delete "$REPO/frontend/dist/" "$SITE_DIR/htdocs/"
fi

# Backend
rsync -a --delete "$REPO/backend/" "$SITE_DIR/src/"

# Demo boards + backgrounds (live data dir, separate from src/)
# Only seed demo boards on a fresh install (no existing *.json in BOARDS_DIR);
# backgrounds always sync since they may be referenced by user boards too.
BOARDS_DIR="$SITE_DIR/boards"
if [[ -d "$BOARDS_DIR" ]]; then
  if ! compgen -G "$BOARDS_DIR/*.json" > /dev/null; then
    rsync -a "$REPO/backend/boards/demo"*.json "$BOARDS_DIR/"
  fi
  rsync -a "$REPO/backend/boards/backgrounds/" "$BOARDS_DIR/backgrounds/"
fi

# Ensure outer Apache WebSocket tunnel config exists (direct ws:// → orbvis backend)
BACKEND_PORT=$(grep -oP -- '--port \K[0-9]+' /omd/sites/CMC/etc/init.d/orbvis 2>/dev/null | head -1 || true)
BACKEND_PORT=${BACKEND_PORT:-8421}
cat > "$OUTER_APACHE_CONF" << APACHEEOF
# OrbVis WebSocket proxy – direct tunnel from outer Apache to orbvis backend.
# This file is managed by deploy-cmc.sh.
# Uses <Location> so it wins over the shorter <Location /CMC> in CMC.conf.
# upgrade=websocket works with mpm_prefork (Apache 2.4.47+).
<Location /CMC/orbvis/api/v1/ws>
  ProxyPass        http://127.0.0.1:${BACKEND_PORT}/api/v1/ws upgrade=websocket
  ProxyPassReverse http://127.0.0.1:${BACKEND_PORT}/api/v1/ws
</Location>
APACHEEOF
if [[ ! -L "$OUTER_APACHE_ENABLED" ]]; then
  ln -sf "$OUTER_APACHE_CONF" "$OUTER_APACHE_ENABLED"
fi
APACHE_PID=$(cat /var/run/apache2/apache2.pid 2>/dev/null || pgrep -o apache2 || true)
if [[ -n "$APACHE_PID" ]]; then
  kill -HUP "$APACHE_PID" && echo "Apache reloaded (PID $APACHE_PID)"
else
  echo "WARNING: Apache PID not found, skipping reload"
fi

# Restart orbvis service as CMC user
sudo -u CMC omd restart orbvis
