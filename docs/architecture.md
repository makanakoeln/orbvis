# OrbVis Architecture

A short, code-grounded overview. For a deeper tour, the source itself is
the source of truth.

## High-level

```
┌──────────────────────────────────────────────────────────────────┐
│  Browser  ──────────────────────────────────────────────────────│
│  Vue 3 SPA · TypeScript · Pinia · Vite · Tailwind · D3 v7        │
└────────────┬──────────────────────────────────────┬──────────────┘
             │ REST + JWT (access + refresh)        │ WebSocket
             │ /api/v1/…                            │ /api/v1/ws/maps/{name}
             ▼                                      ▼
┌──────────────────────────────────────────────────────────────────┐
│  FastAPI backend                                                  │
│  - app/api/v1/        endpoints (auth, maps, states, users, …)    │
│  - app/services/      auth, map, state, backend                   │
│  - app/backends/      livestatus (asyncio), test (demo)           │
│  - app/core/          config, security, websocket, ratelimit, …   │
│  - SQLAlchemy 2.0 async (SQLite default, PostgreSQL supported)    │
└────────────┬───────────────────────────┬─────────────────────────┘
             │ Livestatus (Unix / TCP)   │ optional Checkmk SSO
             ▼                           ▼
┌──────────────────────────────────────────────────────────────────┐
│  Checkmk site                                                     │
│  - tmp/run/live  Livestatus socket                                │
│  - etc/htpasswd  password hashes (SSO fallback)                   │
│  - etc/auth.secret  Checkmk auth-cookie HMAC key                  │
└──────────────────────────────────────────────────────────────────┘
```

## Boards

Boards are stored as JSON files in `BOARDS_DIR` (default
`backend/boards/`, on OMD `$OMD_ROOT/local/share/orbvis/boards/`). Not in
the database — they are content, not state, and are easy to back up
verbatim.

Board types:

- **Static** — manual layout; lines, textboxes, images
- **Flow** — D3 force-directed topology
- **Radar** — severity grid
- **Geo** — Leaflet world map with lat/lng objects and polylines

Object types are unified across board types (host, service, hostgroup,
servicegroup, board link, line, textbox, image, graph, BI). The same
edit panel and properties modal handle all of them.

## State delivery

The state pipeline:

1. `state_service.refresh_loop()` polls the registered backends every
   `STATE_REFRESH_INTERVAL` seconds.
2. Per board, a `BoardConnectionManager` keeps a set of WebSocket
   clients. New states are pushed to all subscribers as
   `{type: "state", payload: …}` JSON frames.
3. Clients get an initial snapshot when they connect (after auth) and
   incremental updates from then on.

The WebSocket auth handshake requires the first message to be
`{type: "auth", token: "<access-token>"}`. The connection is closed if
the token is missing, expired, or on the blocklist.

## Authentication

Two paths, both producing OrbVis JWTs:

1. **OrbVis-native**: bcrypt-hashed passwords in OrbVis' own DB.
2. **Checkmk SSO** (when running inside an OMD site):
   - Validate the `auth_<site>` cookie HMAC against
     `$OMD_ROOT/etc/auth.secret`. Both CMK 2.4 and 2.5+ formats are
     supported (auth_service.py).
   - Fall back to htpasswd verification (SHA1, bcrypt $2y$/$2b$, APR1,
     SHA-crypt) when no cookie is present.
   - Sync admin role from Checkmk's `users.mk` on every login.

## Backends

`backends.json` lists monitoring data sources. Each entry has a `type`
(`livestatus`, `test`, `icinga2`) and the parameters needed to reach it.
`backend_service.register_backend()` instantiates them at startup.

The `livestatus` backend is a pure-asyncio implementation
(`backend/app/backends/livestatus.py`) — Unix sockets and TCP both
supported, with retry and connect-timeout handling.

## Frontend

- `frontend/src/api/client.ts` — typed fetch wrapper, refresh-token
  rotation, automatic re-auth on 401
- `frontend/src/stores/` — Pinia stores: `auth`, `maps`, `states`,
  `backends`. The `states` store owns the WebSocket and reconnects
  automatically on drop.
- `frontend/src/components/map/` — `MapCanvas` (the SVG root), per-type
  object renderers, `HoverMenu`, `ContextMenu`, `EditPanel`,
  `WorldMapCanvas` (Leaflet wrapper).
- `frontend/src/router/index.ts` — hash-mode router with auth guards
  (works behind any reverse-proxy URL).

## Tests

- `backend/tests/` — pytest, async-aware. Security-focused tests live in
  `test_security_hardening.py`, `test_csrf.py`, `test_websocket.py`.
- `frontend/src/**/*.test.ts` — Vitest. Coverage gate is intentionally
  modest at this stage and will rise over time.
- `tools/test_cfg_importer.py` — covers the NagVis import.

## Long-term

Development is moving towards OrbVis being available as a built-in
Checkmk package, in addition to the standalone and MKP-Exchange paths
which remain. For that path, the `upstream-checkmk/` subtree mirrors the
eventual Checkmk source layout (`cmk/gui/orbvis/`,
`packages/cmk-orbvis-frontend/`). It is currently a skeleton; population
is tracked separately.
