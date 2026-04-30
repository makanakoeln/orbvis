# OrbVis vs. NagVis

A practical comparison for users and admins evaluating OrbVis as a
NagVis successor. This is opinionated and pragmatic — not marketing.

## TL;DR

OrbVis covers the everyday NagVis workflow (boards, hosts/services,
lines, weathermaps, hover info, context menus) with a modern stack and
real-time WebSocket updates. A handful of NagVis features are not yet
present (see *Missing*). For most installs the result is a strict
upgrade; for installs that depend on the missing features, OrbVis is
not a drop-in replacement *yet*.

## Stack

| Aspect             | NagVis                        | OrbVis                         |
| ------------------ | ----------------------------- | ------------------------------ |
| Backend language   | PHP 7+                        | Python 3.12 + FastAPI          |
| Frontend stack     | Vanilla JS, jQuery            | Vue 3 + TypeScript + Vite      |
| Map storage        | `.cfg` files                  | JSON files                     |
| Auth store         | SQLite (`auth.db`)            | SQLAlchemy (SQLite/PostgreSQL) |
| State delivery     | Polling via AJAX (~10 s)      | WebSocket push (default 15 s)  |
| Backend protocol   | Livestatus, mklivestatus      | Livestatus (asyncio), Icinga2  |
| RBAC model         | mod / act / obj triples       | mod / act / obj triples (same) |
| Code base size     | ~52 kLOC PHP + JS             | ~30 kLOC Py + ~25 kLOC TS      |
| License            | GPL-2.0-only                  | GPL-2.0-only                   |
| Active development | NagVis 1.9.49 (Apr 2024) [^1] | Active                         |

[^1]: NagVis upstream releases have slowed considerably in recent
years. OrbVis exists in part to give the community a forward-looking
option without forking NagVis.

## Feature parity

Legend: ✅ done · 🟡 partial / different · ❌ not yet · ➕ new in OrbVis.

### Boards & objects

| Feature                                         | NagVis | OrbVis |
| ----------------------------------------------- | ------ | ------ |
| Static map with background image                | ✅     | ✅     |
| Host / service / hostgroup / servicegroup icons | ✅     | ✅     |
| Lines (plain, arrow, dashed)                    | ✅     | ✅     |
| Weathermap lines (bandwidth / metric)           | ✅     | ✅     |
| Textbox                                         | ✅     | ✅     |
| Image / shape                                   | ✅     | ✅     |
| Map links between boards                        | ✅     | ✅     |
| Geo map (lat / lng) with Leaflet                | 🟡 [^2] | ✅     |
| Force-directed topology (Flow board)            | ❌     | ➕     |
| Severity grid (Radar board)                     | ❌     | ➕     |
| Multi-select + bulk move                        | ❌     | ➕     |
| Drag-drop reorder of boards on home screen      | ❌     | ➕     |
| Inline edit panel (vs. modal-only edit)         | ❌     | ➕     |

[^2]: NagVis has *Worldmap* (OpenStreetMap-backed) but lat/lng support
is limited to point objects; lines between two geo coordinates are
OrbVis-only.

### Live data

| Feature                                          | NagVis | OrbVis |
| ------------------------------------------------ | ------ | ------ |
| Livestatus (Unix socket)                         | ✅     | ✅     |
| Livestatus (TCP)                                 | ✅     | ✅     |
| Multiple backends per OrbVis instance            | ✅     | ✅     |
| Real-time push (WebSocket)                       | ❌     | ➕     |
| Acknowledged + downtime indicators               | ✅     | ✅     |
| `only_hard_states`, `recognize_services`         | ✅     | ✅     |
| BI aggregations (Checkmk Business Intelligence)  | ❌     | ➕     |

### Auth & permissions

| Feature                                          | NagVis | OrbVis |
| ------------------------------------------------ | ------ | ------ |
| Built-in user/role management                    | ✅     | ✅     |
| Checkmk SSO via auth cookie                      | 🟡     | ✅     |
| htpasswd verification (multiple hash formats)    | 🟡     | ✅     |
| RBAC (mod / act / obj)                           | ✅     | ✅     |
| Per-board view/edit/use/configure roles          | ✅     | ✅     |
| LDAP                                             | ✅     | ❌     |
| OAuth / SAML                                     | ❌     | ❌     |

### UX & accessibility

| Feature                                          | NagVis | OrbVis |
| ------------------------------------------------ | ------ | ------ |
| Light / dark theme                               | 🟡     | ✅     |
| Configurable hover template                      | ✅     | ✅     |
| Configurable context menu                        | ✅     | ✅     |
| Auto-rotation of board links (kiosk mode)        | ✅     | ✅     |
| Mobile-friendly UI                               | ❌     | 🟡 [^3] |
| Checkmk visual integration (sidebar snapin)      | ❌     | ✅     |

[^3]: Boards render on mobile but the editor is desktop-first.

### Operations

| Feature                                          | NagVis | OrbVis |
| ------------------------------------------------ | ------ | ------ |
| OMD-site native packaging                        | ✅     | ✅ (MKP) |
| .deb / .rpm packages for standalone              | ❌     | ✅     |
| Docker / docker-compose                          | 🟡     | ✅     |
| Hot-reload of map files                          | ✅     | ✅     |
| Database-free map storage (JSON / .cfg)          | ✅     | ✅     |
| Audit log                                        | 🟡     | ❌     |
| API for automation                               | 🟡     | ✅ (FastAPI / OpenAPI) |

## Missing features (we want these too)

These are the most-requested NagVis features that OrbVis does not yet
have. PRs welcome.

- **LDAP authentication** — Checkmk SSO covers most OMD users; standalone
  installs that rely on LDAP currently can't use OrbVis.
- **Audit log** — NagVis keeps a structured edit log; OrbVis logs at
  application level only.
- **All NagVis stock gadgets** — only the most common (gauge, bar) are
  recognised by the importer. Custom gadgets fall back to icons.
- **Plug-in architecture** — NagVis allows custom map sources / actions
  via PHP plugins; OrbVis does not yet expose an extension point.

## When to choose OrbVis today

Pick OrbVis if you want:

- Real-time updates (WebSocket) instead of polling
- A modern, type-safe codebase that's easier to extend
- A force-directed topology view or a severity radar
- Tight Checkmk visual integration (sidebar snapin, menu entry, SSO)
- Native geo lines between two coordinates
- A maintained project for the next few years

Stick with NagVis (for now) if you depend on:

- LDAP authentication (no Checkmk SSO option)
- Custom PHP gadgets / plugins
- A specific NagVis-only feature listed under *Missing* above

## Roadmap

The road from "works for most" to "works for everyone NagVis works for"
is mostly closing the *Missing* list, plus polishing the migration
tooling. See [`ROADMAP.md`](../ROADMAP.md) for the current priorities.
