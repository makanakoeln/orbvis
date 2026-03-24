# Changelog

All notable changes to OrbVis are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning follows [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.1.0] - 2026-03-24

### Added
- Initial release of OrbVis — a complete rewrite of NagVis
- Board editor with SVG canvas, drag-and-drop object placement
- Object types: host, service, hostgroup, servicegroup, map, line, textbox, worldmap, graph (URL embed)
- Real-time state updates via WebSocket
- Multiple monitoring backend support (Livestatus via Unix socket or TCP, demo backend)
- Role-based access control (RBAC) with users, roles, and permissions
- JWT authentication with access and refresh tokens; SSO via Checkmk OMD session cookie
- Dark/light theme, i18n (de/en)
- Admin panel: connections, icon sets, users, roles, global settings
- Legacy NagVis config importer (`tools/cfg_importer.py`)
- Checkmk GUI extensions: sidebar snapin and main menu entry
