#!/bin/bash
# Deploys OrbVis (frontend + backend) to the CMC OMD site.
# Run via: sudo /home/ronny/git/orbvis/deploy-cmc.sh
set -euo pipefail

REPO=/home/ronny/git/orbvis
SITE_DIR=/omd/sites/CMC/local/share/orbvis

# Frontend (only if dist/ exists)
if [[ -d "$REPO/frontend/dist" ]]; then
  rsync -a --delete "$REPO/frontend/dist/" "$SITE_DIR/htdocs/"
fi

# Backend
rsync -a --delete "$REPO/backend/" "$SITE_DIR/src/"

# Restart orbvis service as CMC user
sudo -u CMC omd restart orbvis
