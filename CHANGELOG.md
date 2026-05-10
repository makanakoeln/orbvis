# Changelog

All notable changes to OrbVis are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning follows [Semantic Versioning](https://semver.org/).

## [0.2.0] - 2026-05-10

Iterative release that hardens the operator workflow on top of 0.1.0
without changing any public API.

### BI aggregations
- Drawer summary pane with per-state leaf counts and the worst-leaf
  path
- Bulk-acknowledge confirm modal (capped parallelism, audit-trail
  comment trailer) for all contributing leaves of an aggregation
- WATO setup deep-link from the drawer (`mode=bi_rules&pack=<id>`
  when the pack id is known, otherwise `mode=bi_packs`)
- Live preview of the resulting tree state + glyph-density warning
  in the edit panel
- `exclude_members` regex now shows a live "N suppressed of M"
  feedback line in the object-properties modal
- Stale-data hint in the drawer when the aggregation's federation
  is unhealthy
- Subtree highlight from root to worst leaf in the BI tree gadget

### Group-level actions
- Hostgroup / servicegroup acknowledge + downtime via Checkmk's
  `acknowledge_type=hostgroup|servicegroup` REST surface
- Members tab with triage health, per-row search, last-state-change
- Clickable member rows; hide-zero health chips; responsive controls

### Boards & objects
- Per-object connection override (multi-backend per board)
- Connection picker in object-properties modal
- Worldmap automap source — auto-discover hosts with lat/lng
- Search bar parity for static, worldmap, radar and flow boards
- `Ctrl+Wheel` zoom (with cursor anchor) on static boards
- Settings: Object-defaults section open by default for
  discoverability

### Drawer / detail panel
- Open-in icons resolve absolute paths regardless of bundle
  base-path
- Member states aggregate properly across nested map links
- Force-check / notifications / checks / remove-ack now route
  through the livestatus command pipe
- Group-action errors enriched with WATO-config hints
- Decorative objects (textbox, image, line without host/svc) skip
  the slide-in

### Checkmk integration
- Connections support CMK 2.3 / 2.4 / 2.5 / 2.6 site_config
  signatures
- TCP port is optional (allows unix-socket-only setups)
- Modals close on Escape across the board
- Autocomplete suggestion cap raised to 500 with truncation surface

### Docs / tooling
- `docs/cmk-builtin-readiness.md` — punch-list for shipping OrbVis
  as a Checkmk-builtin in 2.6 (3 blockers, 4 should-fixes
  documented)
- GUI MKP-update test path covered alongside the existing CLI path

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
