# OrbVis backend

FastAPI + SQLAlchemy 2.0 (async). Provides the REST API, WebSocket
state push, auth, RBAC, and Livestatus integration.

## Quickstart (development)

Requirements: Python 3.12+.

```bash
cd backend
pip install -e ".[dev]"
cp .env.example .env
uvicorn app.main:app --reload
```

The API is then on `http://localhost:8000`. Interactive docs:
`http://localhost:8000/api/docs`.

The first start prints a one-time admin password — find it with
`grep 'Default admin' <wherever you redirected stdout>` (or just look
at the terminal).

## Layout

```
app/
  api/v1/        endpoints: auth, maps, states, users, roles, backends, ws
  models/        SQLAlchemy models (user, role, permission, …)
  schemas/       Pydantic v2 request/response models
  services/      auth, map, state, backend (business logic)
  backends/      monitoring backends (livestatus async, test, icinga2)
  core/          config, database, security, websocket, ratelimit, middleware
  main.py        FastAPI app + lifespan
boards/          JSON board files (ignored except demo*.json)
tests/           pytest, async-aware
alembic/         migrations (init_db creates the schema in dev mode)
```

## Configuration

`app/core/config.py` (pydantic-settings). Reads from `.env` plus
environment variables. The fields that matter most for users:

| Variable                  | Default                             | Notes                              |
|---------------------------|-------------------------------------|------------------------------------|
| `DATABASE_URL`            | `sqlite+aiosqlite:///./orbvis.db`   | async URL                          |
| `SECRET_KEY`              | *(must be set in production)*       | 64-hex chars                        |
| `BOARDS_DIR`              | `./boards`                          | board JSON files                   |
| `BACKENDS_FILE`           | `./backends.json`                   | backend definitions                |
| `STATE_REFRESH_INTERVAL`  | `15`                                | seconds                            |
| `ALLOWED_ORIGINS`         | `http://localhost:5173`             | CORS, comma-separated              |
| `CHECKMK_OMD_ROOT`        | unset                               | enables OMD SSO when set           |

See `app/core/config.py` for the full list and defaults.

## Tests

```bash
pytest                          # all
pytest tests/test_auth.py -v    # one file
pytest -k 'security'            # by name pattern
pytest --cov=app --cov-report=term-missing
```

Security-focused tests live in:

- `tests/test_security_hardening.py`
- `tests/test_csrf.py`
- `tests/test_websocket.py`

## Linting and types

```bash
ruff check app tests
ruff format app tests
mypy app
bandit -r app
pip-audit
```

`make precommit` (from the repo root) runs all of the above plus the
frontend checks.

## Adding a new monitoring backend

1. Subclass `app.backends.base.MonitoringBackend`.
2. Implement `connect()`, `disconnect()`, `fetch_states()`, and
   whatever the backend type needs (e.g. host group lookup).
3. Add the type literal to `app/schemas/backend.py`.
4. Register a constructor in `app/services/connection_service.py`.
5. Add tests under `tests/`.

`livestatus.py` and `test.py` are good references.

## See also

- [Architecture overview](../docs/architecture.md)
- [API reference](http://localhost:8000/api/docs) (when running)
- [Contributing](../CONTRIBUTING.md)
