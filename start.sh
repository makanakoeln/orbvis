#!/usr/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

trap 'kill $(jobs -p) 2>/dev/null' EXIT INT TERM

if [[ -f "$SCRIPT_DIR/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$SCRIPT_DIR/.env"
  set +a
fi
export ENVIRONMENT="${ENVIRONMENT:-development}"

cd "$SCRIPT_DIR/backend"

# Schema + default admin are handled by the FastAPI lifespan now; no alembic.
# When CHECKMK_OMD_ROOT is unset the lifespan creates a random-password admin
# and prints it once to stdout, so the first start tells the operator how to
# log in. Subsequent starts find an admin and skip the seeding.

echo "Starting OrbVis backend on :8080 ..."
.venv/bin/uvicorn app.main:app --app-dir . --host 127.0.0.1 --port 8080 --reload &

"$SCRIPT_DIR/backend/.venv/bin/python3" -c "
import socket, time, sys
for _ in range(50):
    try:
        s = socket.create_connection(('127.0.0.1', 8080), timeout=0.2)
        s.close(); sys.exit(0)
    except OSError:
        time.sleep(0.2)
sys.exit(1)
" && sleep 0.5; true

echo "Starting OrbVis frontend on :5173 ..."
cd "$SCRIPT_DIR/frontend"
npm run dev &

echo ""
echo "  Frontend: http://localhost:5173"
echo "  API docs: http://localhost:8080/api/docs"
echo ""
echo "Press Ctrl+C to stop both."

wait
