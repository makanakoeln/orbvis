# Changelog

All notable changes to OrbVis are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning follows [Semantic Versioning](https://semver.org/).

## [0.2.0] - 2026-05-10

Iterative release on top of 0.1.0 with no public-API changes.

### Features

- Flow board: major overhaul — donut/fan/orbit/phyllotaxis layouts, host halo, search + problems-only filter, shift-click and lasso multi-select, in-app detail drawer, right-click context menu
- Flow board: live topology over WebSocket with `TopologyDelta`, persistent host drag positions, site-umbrella root, top-K problem highlighting
- Flow board: pan/zoom performance — rAF-coalesced zoom, GPU-promoted zoom-layer, LoD via single CSS class, force-sim pause during pan, tuned cache/top-K/timeout for large installs
- Detail drawer: redesigned shell on `CmkSlideIn` with tabbed content (Status / Performance / Context / Activity), CMK perfometer headline, sparklines, on-demand long output, topology, comments and downtimes
- BI aggregations: drawer summary pane, bulk-acknowledge of contributing leaves with confirm modal, WATO deep-link, root→worst-leaf subtree highlight, stale-data hint, live tree-state preview and glyph-density warning in the edit panel, live suppression-count for `exclude_members` regex
- Group-level actions: hostgroup / servicegroup acknowledge + downtime via CMK `acknowledge_type`, members tab with triage health, search and last-state-change
- Boards: per-object connection override (multi-backend per board) + picker in object-properties, worldmap automap source for hosts with lat/lng, `Ctrl+Wheel` zoom on static boards, search-bar parity across board types, optimistic locking via `If-Match`, `background_color`, textbox resize handles
- Triage UX: detail-drawer-first workflow with triage breadcrumb, board header dim, context menu trimmed to navigation
- States: delta-encoded WebSocket `state_update` with timing/output fields stripped from the change-detection hash
- Backend: gzip-compressed JSON responses above 1 KiB, in-memory board cache with debounced flush
- Hover: host tooltip with service summary, modifier badges and live countdown
- Checkmk integration: API documentation link in the CMK main menu, Swagger UI served locally behind the OMD Apache proxy, `backends` REST surface renamed to `connections`

### Bug Fixes

- Connections: support CMK 2.3 / 2.4 `site_config` signatures and make TCP port optional for unix-socket-only setups
- Install: launch uvicorn via `python -m` (both `deploy-cmc.sh` and `orbvis-setup`), build venv with `--system-site-packages` for `cmk.licensing`, surface OMD `lib/python3` via `PYTHONPATH`, discover free backend port for multi-site installs
- States: aggregate nested map links so the worst state bubbles up
- Board service: per-board lock around read-modify-write to prevent lost updates under concurrent edits
- Importer: resolve relative coords, per-type defaults, label/textbox fidelity
- Modals: close on Escape across the board
- Drawer: route force-check / notifications / checks / remove-ack via the livestatus command pipe; respect `see_all` admin scope; chip-drilldown filter; open-in icons resolve absolute paths
- Flow board: respect Off mode for service layout, cancel pending fit on operator interaction, harden topology cache for `top-K=0`, scope topology endpoint to auth-user contact groups
- Board: use CMK perfometer percentage in line labels, keep object positions when adding a background image, skip slide-in for decorative objects without host/service
- Refresh enabled sites when `sites.mk` changes

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
