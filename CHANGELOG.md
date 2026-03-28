# Changelog

All notable changes to OrbVis are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning follows [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.1.0] - 2026-03-28

### Added

**Board editor**
- SVG canvas with drag-and-drop object placement and multi-select
- Object types: host, service, hostgroup, servicegroup, board link, line, textbox, worldmap, graph (URL embed)
- Inline edit panel, per-object properties modal, background image upload
- Kiosk mode for unattended display

**Monitoring**
- Real-time state updates via WebSocket (configurable refresh interval)
- Livestatus backend: Unix socket and TCP
- Contact-group filtering via Livestatus `AuthUser` header
- Built-in demo backend for evaluation without a live monitoring system

**Checkmk integration**
- Native WATO permissions: `orbvis.use`, `orbvis.view_all`, `orbvis.edit_all`, per-board `orbvis.view_<name>` / `orbvis.edit_<name>`
- SSO via Checkmk OMD session cookie
- Sidebar snapin listing all accessible boards
- Main menu entry
- Supports Checkmk 2.3 and 2.4+

**Authentication & access control**
- JWT access and refresh tokens
- Role-based access control (RBAC) with users, roles, and permissions
- Admin panel: connections, icon sets, users, roles, global settings

**UI**
- Dark and light theme
- German and English interface

**Installation**
- Native packages for all Checkmk-supported platforms:
  `.deb` (Ubuntu 22.04/24.04, Debian 12/13) and `.rpm` (RHEL 8/9/10, Rocky, AlmaLinux, SUSE 15 SP6/SP7/16)
- Standalone install via `orbvis-install` (systemd + nginx/Apache)
- Checkmk/OMD install via `orbvis-setup <site>`
- Docker Compose for local development
