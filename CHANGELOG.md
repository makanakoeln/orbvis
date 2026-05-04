# Changelog

All notable changes to OrbVis are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning follows [Semantic Versioning](https://semver.org/).

## [0.1.0] - 2026-05-03

Initial release. OrbVis is a modern monitoring visualization platform — a
community successor to NagVis, designed primarily for use inside Checkmk.

### Boards & objects
- Four board types: static, flow (force-directed topology),
  radar (severity grid), geo (Leaflet)
- Host / service / hostgroup / servicegroup icons
- Lines with selectable shape (plain, arrow_end / arrow_start / arrow_both,
  arrow_inward, dashed) plus orthogonal perfdata-label and weather-color
  attributes for bandwidth / utilization-coloured lines
- Textbox, image / shape, map links between boards
- Multi-select + bulk move; inline edit panel
- Configurable hover templates and context menus
- Drag-drop reorder of boards on home screen
- Light / dark theme
- English and German UI

### Live data
- Real-time state push via WebSocket
- Livestatus over Unix socket and TCP, multiple backends
  per instance, Icinga2 backend
- BI aggregations (Checkmk Business Intelligence)
- Acknowledged + downtime indicators,
  `only_hard_states` / `recognize_services` flags
- Hot-reload of board JSON files
- Disk-cached OSM tile proxy for geo boards, with
  configurable `tile_url` and `tile_saturate` overrides

### Checkmk integration
- Main-menu entry, sidebar snapin
- SSO via OMD session cookie, htpasswd fallback
- WATO-driven per-board permissions
  (`orbvis.view_*`, `orbvis.edit_*`)
- Livestatus auto-wiring on OMD sites
- Supports Checkmk 2.3 – 2.6

### Auth & access control
- JWT access + refresh tokens, bcrypt password hashing
- RBAC (mod / act / obj triples) for standalone mode
- Auto-rotation of board links (kiosk mode)

### Operations
- Native packages: `.deb`, `.rpm`; MKPs for Checkmk
  2.3 / 2.4 / 2.5 / 2.6; Docker Compose for development
- NagVis `.cfg` map import via `tools/cfg_importer.py`
- FastAPI / OpenAPI documented REST + WebSocket API

### Known limitations
- LDAP not yet supported (Checkmk SSO works)
- No structured audit log
- No plug-in architecture for custom gadgets
- Custom NagVis PHP gadgets fall back to plain icons
- Editor is desktop-first; boards render on mobile
