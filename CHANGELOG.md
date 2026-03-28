# Changelog

All notable changes to OrbVis are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning follows [Semantic Versioning](https://semver.org/).

## [0.1.0] - 2026-03-28

Initial public release. OrbVis is a ground-up rewrite of NagVis as a modern
monitoring visualization platform — Vue 3 frontend, FastAPI backend, real-time
WebSocket state delivery, and native Checkmk integration.

**Board editor**
- SVG canvas with pixel-accurate drag-and-drop object placement and multi-select
- Inline edit panel and per-object properties modal
- Object types: host, service, hostgroup, servicegroup, board link, line, textbox, image, graph
- Image/icon objects with configurable size, rotation, and arc ring state indicator
- Textbox objects with raw HTML rendering
- Connection lines (plain and weathermap style with bandwidth/metric overlay)
- Metric gadgets: gauge, bar, and traffic-light display modes for service objects
- Per-object URL field; Checkmk host/service URL auto-derived as placeholder
- Board link objects show aggregated worst state from the referenced board
- Stale state indicator when monitoring data is outdated
- Configurable hover template and context menu template per object
- `only_hard_states` and `recognize_services` options per object
- Background image upload for boards
- Object duplication via context menu
- Board settings modal (connection, refresh interval, background, permissions)
- Default icon size setting applied to newly placed objects
- Kiosk mode for unattended display with rotation countdown and pause/resume
- Board-link rotation with configurable interval

**Monitoring**
- Real-time state updates via WebSocket (configurable refresh interval)
- Livestatus backend supporting both Unix socket and TCP connections
- Batch host/service queries to minimize Livestatus round-trips
- Connection semaphore and query timeout to protect against backend overload
- Contact-group filtering via Livestatus `AuthUser` header
- CMC (Checkmk Micro Core) auto-detection and compatible rrddata query format
- Demo backend with deterministic states for evaluation without a live system

**Native metric charts**
- Embedded D3.js time-series charts inside graph objects
- Fetches rrddata history via Livestatus perf_data (Nagios Core / CMC)
- Checkmk REST API metric history for Checkmk Raw Edition
- Optional automation user/secret for Checkmk Raw metric history
- Human-readable metric titles and units sourced from Checkmk graphing plugins
- Multi-series charts with warn/crit threshold lines
- SI unit scaling with smart prefix detection (handles MB/GB/TB without double-scaling)
- Formatted legend with metric name, current value, and unit
- Theme-aware chart colors (light and dark mode)
- Configurable time window per graph object

**Topology / flow board**
- Force-directed network topology board type derived from Livestatus `parents` column
- Host spacing with configurable repulsion, optional service nodes
- Auto-fit zoom when service layout changes

**Radar board**
- Card-grid board type listing all monitored objects sorted by severity
- State summary bar with per-state counts; color-coded cards by state

**Worldmap**
- Leaflet-based worldmap board type
- NagVis-compatible geo features: host geo lookup from Livestatus custom variables
- ARC ring overlay on map markers

**Actions**
- Acknowledge, schedule downtime, and force-check from object context menu
- Checkmk REST API integration for ack/downtime/force-check (Checkmk 2.4+)
- Acknowledgement and active downtime badges on object icons

**Checkmk integration**
- Supports Checkmk 2.4, 2.5, and 2.6
- Native WATO permissions: `orbvis.use`, `orbvis.view_all`, `orbvis.edit_all`,
  per-board `orbvis.view_<name>` / `orbvis.edit_<name>`
- SSO via Checkmk OMD session cookie (HMAC verification compatible with CMK 2.4 and 2.5)
- Auto-create Livestatus connection on startup in Checkmk mode
- Sidebar snapin listing all accessible boards
- Main menu entry (compatible with CMK 2.4/2.5/2.6 menu APIs)
- MKP packaging for Checkmk 2.3+ extension marketplace

**NagVis import**
- `.cfg` import: upload a NagVis map file directly in the board editor
- Batch importer (`tools/cfg_importer.py`) converts entire NagVis map directories
- Supports nested label/display fields, line coordinates, shape→image mapping

**Authentication & access control**
- JWT access and refresh tokens; token blocklist on logout
- Login rate limiting (failed attempts only)
- Role-based access control (RBAC) with users, roles, and fine-grained permissions
- Admin panel: monitoring connections, icon sets, users, roles, global settings

**Onboarding**
- Spotlight tour for first-time users covering navigation, boards, and settings
- Gamification: step completion tracking, animated demo objects on the canvas step
- Custom graph style in tour with realistic warn/crit visualization
- Tour skips Checkmk-specific navigation steps when running inside an OMD site
- Tour reset option in user settings; keyboard navigation throughout

**UI / UX**
- Dark and light theme
- German and English interface
- Toast notifications for save, delete, and error feedback
- Changelog popup on first login after a version update
- Autocomplete for host, service, and metric name fields
- Confirm dialogs replace native browser `confirm()` throughout
- Search with clear button on home screen; clone dialog with alias field
- Back navigation button always visible in board view

**Security**
- XSS hardening: `Content-Security-Policy`, `X-Frame-Options`, `X-Content-Type-Options` headers
- Replaced `python-jose` with `PyJWT` (eliminates ecdsa CVE-2024-23342)
- Downgraded `vitest` to 4.0.18 (fixes flatted prototype-pollution CVE)
- Icinga2 filter input escaping

**Installation**
- Native packages for all Checkmk-supported platforms:
  `.deb` (Ubuntu 22.04/24.04, Debian 12/13) and
  `.rpm` (RHEL 8/9/10, Rocky Linux, AlmaLinux, SUSE 15 SP6/SP7/16)
- Standalone install via `orbvis-install` (systemd service + nginx/Apache reverse proxy)
- Checkmk/OMD install via `orbvis-setup <site>`; auto-detects free port per site
- Docker Compose for local development

**Tooling & CI**
- GitHub Actions for frontend (lint, type-check, test, build) and backend (mypy, ruff, pytest)
- Pre-commit hook: ruff format+check, mypy, prettier, stylelint
- Pre-push hook: full frontend and backend test suite, npm audit
- Comprehensive unit and integration test coverage for backend services and frontend stores
