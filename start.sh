#!/usr/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Kill child processes on exit
trap 'kill $(jobs -p) 2>/dev/null' EXIT INT TERM

cd "$SCRIPT_DIR/backend"

# Run database migrations before starting the server (fresh install or upgrade)
echo "Running database migrations..."
.venv/bin/python3 -m alembic upgrade head

# Ensure admin/admin user exists (no forced password change)
echo "Setting up dev admin user..."
"$SCRIPT_DIR/backend/.venv/bin/python3" - <<'PYEOF'
import asyncio, sys
sys.path.insert(0, '.')

async def main():
    from app.core.database import AsyncSessionLocal
    from app.core.security import hash_password
    from app.models.user import User
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.name == 'admin').limit(1))
        user = result.scalar_one_or_none()
        if user is None:
            user = User(name='admin', password=hash_password('admin'), is_active=True, is_admin=True, must_change_password=False)
            db.add(user)
        else:
            user.password = hash_password('admin')
            user.is_admin = True
            user.must_change_password = False
        await db.commit()

asyncio.run(main())
PYEOF

echo ""
echo "============================================"
echo "  Admin login:    admin / admin"
echo "============================================"
echo ""

echo "Starting OrbVis backend on :8080 ..."
cd "$SCRIPT_DIR/backend"
.venv/bin/uvicorn app.main:app --app-dir . --host 127.0.0.1 --port 8080 --reload &

# Wait until the backend accepts connections before starting the frontend
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
