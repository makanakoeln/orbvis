# Orbvis

Monitoring visualization platform built with **Python FastAPI** + **Vue.js 3 + TypeScript**.

## Requirements

- Python 3.12 or newer
- Node.js 18 or newer (for building the frontend)
- systemd (for the standalone install)

## Installation

### Standalone (without Checkmk/OMD)

Installs to `/opt/orbvis`, creates a system user, sets up a Python virtualenv, builds the
frontend, and configures a systemd service. nginx is configured automatically if present.

```bash
./install.sh
```

The default admin password is printed once on first start:

```bash
sudo journalctl -u orbvis --no-pager | grep 'Default admin'
```

To uninstall (user data is kept):

```bash
./install.sh remove
```

### With Checkmk / OMD

Tested with **Checkmk 2.4**. Deploys orbvis into an existing OMD site, wires up the site's
Apache and registers an OMD init script so `omd start/stop orbvis` works.

```bash
./install_cmk.sh <site-name>
```

orbvis will be available at `https://<host>/<site>/orbvis/`.
Add the **orbvis Maps** sidebar snapin via *Edit sidebar → orbvis Maps*.

To uninstall:

```bash
./install_cmk.sh <site-name> remove
```

### With Docker Compose

```bash
mkdir -p data/maps
docker compose up --build
```

- Frontend: http://localhost:3000
- API docs: http://localhost:8000/api/docs

Default credentials: `admin` / printed in the backend container log on first start.

## Development

**Backend:**
```bash
cd backend
pip install -e ".[dev]"
cp .env.example .env   # edit as needed
uvicorn app.main:app --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

## Configuration

Copy `backend/.env.example` to `backend/.env` and adjust:

| Variable                  | Default                     | Description                        |
|---------------------------|-----------------------------|------------------------------------|
| `DATABASE_URL`            | `sqlite+aiosqlite:///...`   | SQLAlchemy async database URL      |
| `SECRET_KEY`              | *(must be set)*             | JWT signing key (`secrets.token_hex(32)`) |
| `MAPS_DIR`                | `./maps`                    | Directory where map JSON files live |
| `BACKENDS_FILE`           | `./backends.json`           | Backend definitions                |
| `STATE_REFRESH_INTERVAL`  | `15`                        | Seconds between state refreshes    |
| `ALLOWED_ORIGINS`         | `http://localhost:5173`     | CORS allowed origins               |

Backend connections are defined in `backends.json` (see `backends.json.example`).

## Architecture

```
orbvis/
├── backend/        Python 3.12 + FastAPI + SQLAlchemy 2.0 (async)
├── frontend/       Vue 3 + TypeScript + Vite + Tailwind CSS
├── tools/          cfg_importer.py – converts legacy NagVis .cfg maps to JSON
├── install.sh      Standalone install/remove (systemd + optional nginx)
├── install_cmk.sh  Checkmk/OMD install/remove
└── docker-compose.yml
```

## Import legacy NagVis maps

```bash
# Single file
python tools/cfg_importer.py /path/to/nagvis1/etc/maps/mymap.cfg ./data/maps

# Batch import entire maps directory
python tools/cfg_importer.py --batch /path/to/nagvis1/etc/maps/ ./data/maps
```

## API Reference

Interactive docs: http://localhost:8000/api/docs

Key endpoints:

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/auth/login` | Obtain JWT tokens |
| `GET`  | `/api/v1/maps` | List maps |
| `GET`  | `/api/v1/maps/{name}` | Map config + objects |
| `GET`  | `/api/v1/maps/{name}/states` | Current monitoring states |
| `WS`   | `/api/v1/ws/maps/{name}` | Real-time state push |

## Running Tests

**Backend:**
```bash
cd backend
pytest
```

**Frontend:**
```bash
cd frontend
npm test
```

**Import tool:**
```bash
cd tools
pytest test_cfg_importer.py
```
