# Changelog

All notable changes to OrbVis are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning follows [Semantic Versioning](https://semver.org/).

## [0.1.0] - 2026-04-26

Initial public release. OrbVis is a modern monitoring visualization platform —
Vue 3 frontend, FastAPI backend, real-time WebSocket state delivery, and native
Checkmk integration.

**Boards & editor**
- Static, flow (force-directed topology), radar (severity grid), and geo (Leaflet)
  board types with a unified SVG canvas and pixel-accurate drag-and-drop editor
- Object types: host, service, hostgroup, servicegroup, board link, line, textbox,
  image, graph; multi-select, duplication, inline edit panel + properties modal
- Connection lines (plain and weathermap with bandwidth/metric overlay) — also on
  geo maps with `lat2`/`lng2` endpoints and full label config
- Per-object URL field with auto-derived Checkmk host/service link; board-level
  `click_action` setting inherited by all objects
- Background image upload, configurable hover and context-menu templates,
  `only_hard_states` and `recognize_services` per object
- Kiosk mode with rotation countdown and pause/resume; board-link rotation
- Drag-drop board reordering on the home screen with persistent `sort_order`

**Hover & context menu**
- Unified hover menu across all board types — viewport-aware positioning that
  flips next to the icon (not over it) when space is tight
- Acknowledged and downtime state shown directly in the status line, plus
  pill-style badges
- Embedded Checkmk perfometer (replaces utilization sparkline); falls back to
  generic perf-data bars when no Checkmk backend is configured
- Acknowledge, schedule downtime, remove downtime, and force-check from the
  context menu (Checkmk REST API, 2.4+); "Problem services" entry for host objects

**Native metric charts**
- ECharts time-series charts inside graph objects with CMK-style aesthetics
- Multi-series, warn/crit threshold lines, theme-aware colors (light + dark)
- SI/IEC unit scaling with smart prefix detection; metric titles and units
  sourced from Checkmk graphing plugins
- rrddata via Livestatus `perf_data` (Nagios Core / CMC) and Checkmk REST API
  metric history (Checkmk Raw, optional automation user/secret)

**Monitoring backends**
- Real-time state updates via WebSocket (configurable refresh interval)
- Livestatus client over Unix socket and TCP, with batch host/service queries,
  connection semaphore, and query timeout
- Contact-group filtering via Livestatus `AuthUser` (skipped for users with
  Checkmk `general.see_all`); CMC auto-detection and CMC-compatible rrddata
- Demo backend with deterministic states for evaluation

**Checkmk integration**
- Supports Checkmk 2.3, 2.4, 2.5, and 2.6
- SSO via Checkmk OMD session cookie (HMAC verification compatible with 2.4 + 2.5)
- Native WATO permissions: `orbvis.use`, `orbvis.view_all`, `orbvis.edit_all`,
  per-board `orbvis.view_<name>` / `orbvis.edit_<name>`, plus dedicated
  `orbvis.configure` for admin menu access
- Sidebar snapin and main menu entry (compatible with CMK 2.4/2.5/2.6 menu APIs,
  including CMK 2.6 `NavItemIdEnum` / `NavItemTopic`)
- Auto-create Livestatus connection on startup in Checkmk mode
- CMK design tokens (corporate green accent, CMK density and font sizes), CMK
  component shims (Button, Input, Dropdown, Checkbox, ColorPicker, AlertBox,
  Switch, Badge, Collapsible, ToggleButtonGroup, ScrollContainer)

**Map import**
- Upload a legacy `.cfg` map file directly in the board editor
- Supports nested label/display fields, line coordinates, shape→image mapping

**Authentication & access control**
- JWT access and refresh tokens with rotation and reuse rejection; in-memory
  token blocklist on logout
- Login rate limiting and WebSocket connect rate limiting; short auth timeout
  on the WS handshake
- Role-based access control (RBAC) with users, roles, and fine-grained
  permissions; admin panel for connections, icons, users, roles, and settings
- `SECRET_KEY` required in production (fails fast instead of using an ephemeral
  fallback); CSRF origin check for cookie-based mutations; tightened CORS

**Security**
- XSS hardening: `Content-Security-Policy`, `X-Frame-Options`,
  `X-Content-Type-Options` headers
- SVG upload validated with `defusedxml` (XXE + billion-laughs); image upload
  path-traversal rejected via `is_relative_to` + separator check
- Replaced `python-jose` with `PyJWT` (eliminates ecdsa CVE-2024-23342)
- Icinga2 filter input escaping
- Backend Docker image runs as unprivileged user (uid 10001)

**UI / UX**
- Dark and light theme; German and English interface
- Toast notifications, confirm dialogs (replace native `confirm()`), autocomplete
  for host/service/metric fields
- Changelog popup on first login after a version update
- Search with clear button on home; clone dialog with alias field; back-nav
  always visible in board view

**Onboarding**
- Spotlight tour for first-time users with step tracking and animated demo
  objects on the canvas step; tour skips Checkmk-specific steps inside an OMD
  site; tour reset option in user settings; keyboard navigation throughout

**Installation**
- Native packages for all Checkmk-supported platforms:
  `.deb` (Ubuntu 22.04/24.04, Debian 12/13) and
  `.rpm` (RHEL 8/9/10, Rocky Linux, AlmaLinux, SUSE 15 SP6/SP7/16)
- Standalone install via `orbvis-install` (systemd + nginx/Apache reverse proxy)
- Checkmk/OMD install via `orbvis-setup <site>` with auto-detected free port,
  including an `uninstall` subcommand that preserves user data
- MKP packaging for Checkmk 2.3+ extension marketplace
- Docker Compose for local development

**Tooling & CI**
- Tooling aligned with Checkmk: ruff (full CMK rule set), mypy strict (CMK 1:1),
  pytest config, EditorConfig
- Pre-commit + pre-push hooks (consolidated from husky/lint-staged), with
  ruff format/check, mypy, prettier, stylelint, gitleaks, bandit
- GitHub Actions for frontend (lint, type-check, test, build) and backend
  (mypy, ruff, pytest); coverage gates and Docker smoke test in CI
- Comprehensive unit and integration tests for backend services and frontend
  stores, including WebSocket fault-handling and router/api-client coverage
