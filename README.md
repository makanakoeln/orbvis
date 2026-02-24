# NagVis 2

A complete rewrite of NagVis using **Python FastAPI** + **Vue.js 3 + TypeScript**.

## Architecture

```
nagvis2/
├── backend/        Python 3.12 + FastAPI + SQLAlchemy 2.0 (async)
├── frontend/       Vue 3 + TypeScript + Vite + Tailwind CSS
├── tools/          Import tool for legacy NagVis .cfg files
└── docker-compose.yml
```

## Quick Start

### With Docker Compose

```bash
mkdir -p data/maps
docker compose up --build
```

- Frontend: http://localhost:3000
- API docs: http://localhost:8000/api/docs

### Development

**Backend:**
```bash
cd backend
pip install -e ".[dev]"
cp .env.example .env
uvicorn app.main:app --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

### Import legacy maps

```bash
# Single file
python tools/cfg_importer.py /path/to/nagvis1/etc/maps/mymap.cfg ./data/maps

# Batch import entire maps directory
python tools/cfg_importer.py --batch /path/to/nagvis1/etc/maps/ ./data/maps
```

## API Reference

Interactive docs available at http://localhost:8000/api/docs

Key endpoints:
- `POST /api/v1/auth/login` – Get JWT tokens
- `GET /api/v1/maps` – List maps
- `GET /api/v1/maps/{name}` – Map config + objects
- `GET /api/v1/maps/{name}/states` – Current monitoring states
- `WS /api/v1/ws/maps/{name}` – Real-time state updates

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
