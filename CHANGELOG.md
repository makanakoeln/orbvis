# Changelog

All notable changes to OrbVis are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning follows [Semantic Versioning](https://semver.org/).

## [0.6.0] - 2026-06-12

Iterative release on top of 0.5.0. A new design-first **Presentation board**
joins the lineup, metric rendering moves onto Checkmk's own unit-format registry
across every board and the detail drawer, a broad security pass replaces
tokens-in-URLs with short-lived stream tickets and gates Livestatus on the
caller's visibility, and a large internal refactor splits the heavy views into
focused, individually tested composables.

### Features

- **Presentation board (new, experimental)**: a design-first editor — template gallery, **connect-data mode** with a guided host → service → metric walkthrough, a drag-and-drop data browser, and a docked inspector with tabbed panels and explicit save. Elements bind to hosts, services, hostgroups, servicegroups and BI aggregations; slide background images upload straight from the inspector
- **Checkmk-native metric rendering**: values across all boards and the detail drawer format through Checkmk's unit-format registry, so they read exactly as they do in Checkmk; metric pickers and object-detail titles source Checkmk's own metric titles
- **Native metric graphs**: the on-board chart now reads like Checkmk's own — axis and legend in Checkmk's registry units (interface traffic in Mbit/s, not raw octets), series titled from the registry ("Input bandwidth"), graph templates matched through Checkmk's perfvar translation, and bidirectional graphs (interface in/out, disk read/write, …) mirrored below a zero-centred axis; tooltips title their rows and stay on-screen
- **Gadgets**: new **raw-value gadget** (NagVis `rawNumbers`) with a Checkmk time-formatted fallback; perfometer-backed gauge fill; threshold-only metrics render as an absolute value with proportional fill; gadgets show Checkmk's rendered value instead of a percentage faked from a bare `max`
- **Geo board**: bundle selected markers into a single worst-state **location icon**; multi-select editing parity with static boards (group move, marquee, layering)
- **Weathermap / lines**: two-way (bidirectional) weathermap links, working connector labels and dashes, sticky connectors, and bound-line endpoints anchored on the object edge so arrowheads stay visible
- **Unified interaction model**: hover, click and context-menu behaviour are now consistent across every board type; dynamic groups surface linked host and service member pills
- Home overview gains presentation and folder board card previews

### Changed

- **Large internal refactor**: the heavy views were split into ~40 focused composables and utils (flow, detail drawer, folder tree, worldmap, presentation editor), and the Checkmk URL builders, Livestatus command builders, auth scoping and BI maps were consolidated to remove duplication
- Presentation object pickers render as cmk dropdowns and tabs
- Topology wire types moved out of the API layer into the schema layer (service-layer dependency-inversion fix)
- The cmk graphing-data loader moved to `cmk_plugins`, dropping a duplicate title walk
- stylelint documented as droppable OrbVis-only tooling; dead disables removed

### Security

- SSE and map-tile URLs use short-lived **stream tickets** instead of access tokens carried in the URL; the tile proxy now requires auth and caps its disk cache
- Livestatus commands are gated on **AuthUser-scoped target visibility**; monitoring detail endpoints are scoped to the caller's contact groups; object edit context-menu actions are gated to edit mode
- XSS: a control-character bypass in board URL validation is closed via a scheme allowlist, and regex metacharacters are escaped in the autocomplete Livestatus filter
- Upload hardening: SVG uploads pass through XXE/script guards (DOCTYPE / internal-use / data-raster allowed), GIFs are rejected by magic bytes, built-in icons are protected from overwrite, and upload stems are sanitised
- The graph iframe drops `allow-same-origin` and guards embed sinks to http(s)
- `settings.json` / `connections.json` read-modify-write is serialised against lost updates; a runtime instance is unregistered when its connection is deleted
- User rename returns 409 on conflict, self-service fields are restricted, and command separators are rejected in host/service action names

### Fixed

- Login no longer double-submits or raises an unhandled rejection on failure, and now triggers on click/Enter (CmkButton fires no native submit)
- The board autocomplete dropdown is teleported so the inspector panel can no longer clip it
- A presentation element's gadget/flow metric resets when its binding changes
- The legacy board settings modal adopts the save response, so a stale alias/version no longer 409s on the next save
- Hover PENDING pill links to the Checkmk `svcstate` stp filter
- Board import validates the board name so unsafe names can't silently vanish on flush
- NagVis import resolves `line_type` from template/global and defaults weathermap metrics
- Static board no longer flickers at the default (fit) zoom in fullscreen — the canvas is sized via CSS at fit so a space-stealing scrollbar can't oscillate it
- Dragging a static-board object to an edge no longer re-anchors every other object on the next reload — the editor persists the canvas size so the percent-positioning divisor stays identical between editing and reload

## [0.5.0] - 2026-06-07

Iterative release on top of 0.4.1. The Folder board graduates into a fast,
treemap-first surface that scales to six-digit host counts, the frontend
completes its move onto Checkmk's design system, and a hardened release-test
pipeline (real upgrade-from-release tests, input sweeps across every settings
surface) caught and fixed a series of regressions before they could ship.

### Features

- **Folder board, treemap-first**: the board now opens in the Map (treemap) view by default — row details moved to hover, bulk acknowledge/downtime to right-click; the list stays one click away
- **Folder board at scale**: per-tick **SSE delta** updates instead of full-tree pushes, virtualized list rendering and pixel-culled map tiles, a leaner states payload and a single-pass tree build with paused GC — tested against 113k hosts / 4M services
- **Folder board operator tools**: server-side service search (`s:`) that scales to millions of services, quicksearch-operator alignment, auto-expand to reveal matches, a *Problem severity* threshold for the problems-only filter (any vs. critical-only), per-board site scoping with a site picker, OK-host counts in the breakdown and live status refresh without navigating
- **Per-site trust**: when a federation site stops responding, its hosts freeze as *stale* (last known state) with a visible warning instead of silently flapping to UNKNOWN
- **Lines**: NagVis bent lines import faithfully (explicit middle point), a *Remove bend* context action, per-line z-layering plus a board-wide `default_z`, and weathermap lines accept a second (outbound) metric
- **Status visibility**: custom icons are tinted by object status with a solid ring, search matches are desaturated/raised above dimmed objects, and the *show only problems* toggle is available on every board type
- **Checkmk deep-links**: hover pills open the filtered service view, and host/service names in the detail drawer link to their Checkmk pages
- **BI drawer polish**: worst-leaf plugin output, multi-host labels, seeded drilldown and no-op command buttons removed
- Checkmk status palette now also applies to standalone deployments
- Checkmk-mode Livestatus single-site queries route through `cmk.livestatus_client` with a fast JSON parse path

### Changed

- **Frontend on Checkmk's design system**: Tailwind removed in favor of scoped CSS on cmk tokens across all views and components, cmk-frontend-vue strict tsconfig and prettier conventions adopted, the vendored cmk tree refreshed to current master, and `dompurify`/`vueuse`/`vue-draggable-plus` replaced with cmk-style natives
- **i18n migrated** from vue-i18n to vue3-gettext following cmk conventions; locale compilation is deterministic and quiet
- `upstream-checkmk/` now carries the complete built-in integration payload (`cmk/gui/orbvis` module + unit tests, `cmk-orbvis-frontend` package via the sync pipeline)
- Geo-board tile proxy complies with the OSM tile usage policy (bare host rotation, proper user agent, cache revalidation)
- Routine logs quieted: per-tick warmup lines moved to debug, bundled demo boards ship without legacy keys

### Security

- Host/service actions are gated on granular Checkmk command permissions instead of a blanket admin check
- Board create/configuration is gated on `orbvis.edit_all`/configure permissions instead of admin
- BI aggregation titles and trees are scoped to the requesting user's contact visibility
- Login redirects into Checkmk's 2FA challenge instead of dead-ending with a hint

### Fixed

- `omd restart` could kill the OrbVis service when a graceful shutdown hung: the old process kept the port, the new one crashed on bind — the init script now escalates to `kill -9` and uvicorn caps graceful shutdown at 5s
- Settings pages after the cmk vendor refresh: section navigation filters again, every toggle switch works again (model rename + a native-label double-toggle that affected board settings and the color inputs too), and the boards-overview view toggle is compact again
- The *copied* clipboard icon in the detail drawer is bundled — Checkmk themes before 2.5 don't ship it
- Healthy BI aggregations could render PENDING (falsy-zero state) and a shared status-fetcher race returned other users' scopes; structure queries now run unscoped with the auth user resolved per request
- `make_mkp.sh --version` now reaches the frontend bundle, so the UI version and the changelog-modal gate match the packaged version
- `/api/changelog` was empty in MKP installs (changelog/version now copied into the backend source tree)
- Folder board: settings save no longer reports a 409 after the view-preference auto-save, and the live preview reflects unsaved settings
- CI lint gap closed (tool configs cleaned, strict mypy annotation in the BI branch fallback)

## [0.4.1] - 2026-06-01

Point release on top of 0.4.0. Adds the (experimental) **Folder board** — a SETUP folder-tree visualization — behind a feature flag, a matching feature flag for graph objects, plus Flow Board fixes and Checkmk-palette alignment.

### Features

- **Folder board (SETUP folder tree)**: a board that builds itself from the Checkmk SETUP folder hierarchy with worst-state bubbling. Switchable Map (treemap, problems dominate) and List (tree) views with a persisted default; lazy per-host service loading that scales to very large sites; severity-sorted services, command-state badges (ACK/DT/FLAP) and "since" ages; search with quicksearch prefixes and a problems-only toggle; bulk acknowledge/schedule-downtime for all hosts in a folder (recursion toggle + live count); host/service detail drawer with force-check, ack, downtime, comments and "Open in Checkmk".
- **Feature flag**: the Folder board type is gated behind a new *System Settings → Features → Enable Folder boards* toggle (off by default), and labelled *(experimental)* in the board-type picker. Existing folder boards keep rendering regardless.
- **Graph objects feature flag**: the (experimental) graph object type is now gated behind *System Settings → Features → Enable Graph objects* (on by default); existing graph objects keep rendering when it's off.
- **Checkmk status palette**: in a Checkmk deployment, boards adopt Checkmk's own monitoring status colors (facelift/modern-dark `$color-state-*`) instead of OrbVis' standalone primaries, in both light and dark themes.

### Security

- Folder board respects Checkmk permissions: host/service visibility follows contact groups (Livestatus AuthUser); the SETUP folder skeleton follows folder-read permission (`wato.see_all_folders` or folder contact groups) so a scoped user never sees folder names outside their access; commands stay admin-only. SSE subscribers/snapshots are keyed by a permission signature so an admin and a see-all guest get correctly different folder trees.

### Fixed

- Folder Map: first expand of a host rendered its service tiles mis-sized/uncolored until reopened (interrupted entrance transition).
- Folder Map: hover tooltips could overflow the viewport edge — they now flip to stay in view.
- Folder Map: faint container tints washed out to muddy pastels in light mode.
- Folder boards: bulk/command affordances are hidden from users without command permission instead of failing on click.
- Flow Board: host/service **next-check** (and "overdue") now updates live instead of freezing until a full page reload — check-timing travels on the topology channel.
- Flow Board: nodes now show **command-state markers** (acknowledged / in downtime / notifications-disabled), matching the static board.
- Flow Board: host/service commands (acknowledge, downtime, force-check, …) route to the host's actual monitoring site in distributed setups instead of defaulting.
- Flow Board: the detail drawer and hover tooltip reflect live state/timing changes for the open node without reopening.
- Case-insensitive duplicate board names are rejected on create/clone.
- Packaging: fresh MKP/wheel builds no longer fail on a duplicate bundled seed-board path.

## [0.4.0] - 2026-05-26

Iterative release on top of 0.3.0. Boards gain a dynamic-group object type and a NagVis-faithful render mode, board settings become an in-place live-preview editor, and the backend sheds its heavy dependencies for a lean standard-library core.

### Changed

- Live updates now use **Server-Sent Events (SSE)** instead of WebSockets, with an automatic polling fallback. This rides through Checkmk's double-Apache proxy without special WebSocket-upgrade handling. The frontend negotiates the transport on its own — no configuration change needed.
- **Leaner backend**: SQLAlchemy, Alembic and the `websockets` library are gone, replaced by the Python standard library (`sqlite3`, a built-in JWT implementation, env parsing). Fewer dependencies to ship and a smaller offline wheelhouse for air-gapped MKP installs. The local store is now SQLite-only — PostgreSQL is no longer supported (existing SQLite `DATABASE_URL` values keep working unchanged).
- Release artefacts are split into a standalone bundle (`.deb` / `.rpm`) and a Checkmk bundle (MKP), each carrying only what its target needs.

### Features

- **Dynamic groups (dyngroup)**: a new board object that resolves its members live from a Livestatus filter, with an edit UI (filter textarea + type picker), a members tab in the detail drawer and a dedicated member-details endpoint
- **NagVis classic render mode**: draws boards 1:1 the way NagVis did, for faithful `.cfg` imports — selectable per board and globally
- **Board overview**: table-view toggle, bulk edit/export, bulk-delete via hover checkboxes, and per-board permission gating that hides columns and actions you can't use; board flags now sit inline next to the name
- **Board settings reworked into a live-preview editor**: a side-by-side preview pane reflects every change as you make it, with section jump-navigation, host/group autocomplete, quick clone & export, a keyboard save shortcut and Checkmk-style confirm/discard dialogs; flow topology is now edited as a FormSpec
- **Static-board navigation**: wheel-zoom without holding Ctrl, drag-to-pan and a sticky search bar; the quicksearch operator dropdown and `h:` / `s:` / `hg:` / `sg:` / `id:` prefixes now work on flow and radar boards too
- **Connections**: TLS for TCP Livestatus, a transport dropdown, neutral placeholders with client-side validation and consistent label/id display across all dropdowns; invalid entries are skipped at startup instead of crashing the service
- **Importer fidelity**: NagVis textbox font-size/weight/alignment with HTML-entity decoding, `[name]` macro and `label_width` resolution, textbox border/background defaults
- API documentation page now serves Swagger UI 5 from Checkmk when available

### Security

- Dynamic-group Livestatus filters are hardened against header injection
- SSO cookies are rejected when the Checkmk session has not completed 2FA
- Dependency bump for `brace-expansion` (GHSA-jxxr-4gwj-5jf2)
- The `fastapi` dependency excludes the malicious 0.136.3 release (MAL-2026-4750), which pulls a backdoored `fastar` package at install time

### Bug Fixes

- Livestatus client imports work across Checkmk 2.3–2.5 again (`LivestatusResponse` from the top-level module)
- The MKP init script is written atomically so an auto-refresh restart can't corrupt it
- Flow board applies per-board root / child-layers / parent-layers on every topology push
- Weathermap lines: redundant colour fields are hidden when weather colouring overrides them, save is blocked when a metric is missing, and the gradient fades only when the two metrics differ
- Worldmap labels get a tight outline and pixel-snapped offset, fixing smudging at small sizes
- Static-board zoom pins the canvas so the background image scales with the objects
- Radar empty-state points at the board-settings gear instead of a removed on-demand filter
- Board canvas pins its extents at load, so dragging one object no longer shifts the rest
- The native colour picker dismisses cleanly when its input unmounts
- Standalone: skip the SSO probe, proxy `/orbvis/images/` so built-in icons render, and return a null perfometer for non-Livestatus backends
- Importer no longer matches a background colour as the textbox text colour
- `nagvis_classic` icon width is clamped when the image size is unset
- Flow board settings save no longer reports "Board changed elsewhere" after a background layout write (service-layout switch or host drag)
- Board search opens the operator dropdown on the first `/` keystroke; quicksearch prefixes are case-sensitive (lowercase only) to match Checkmk
- Check timing (next check / overdue) refreshes live again instead of freezing on board load, so "check overdue" no longer grows with the time the board stays open
- Replacing or removing a board background now only takes effect on save — closing the settings without saving no longer persists it

## [0.3.0] - 2026-05-18

Iterative release on top of 0.2.0. Settings, connections and dialogs now follow Checkmk's look and feel, and OrbVis can run standalone outside Checkmk.

### Features

- Settings redesigned in Checkmk's WATO style with a master/detail layout, sticky save bar, per-group "modified" badges and a one-click reset to factory defaults on every field
- Connection editor reworked: pick between Unix socket and TCP, with the OMD socket prefilled and clearer credential grouping
- Board editor: dedicated "+" button to add objects, action bar follows the selected object, properties popup can be moved around, fewer accidental selects and double-clicks
- Board canvas: zoom now scales the background and objects together, text-mode objects render as state-colored text, custom icons get a soft highlight
- Image library: separate tabs for built-in and uploaded images, search, drag-and-drop upload for board backgrounds, clearer "image in use" warning with quick links
- Detail drawer is now a slimmer non-modal slide-in with a state-colored edge — easier to keep open while you work
- BI aggregations: bulk-acknowledge contributing leaves, summary/details toggle, respect for the configured expand depth
- Board filter accepts the same prefixes as Checkmk's quicksearch (`h:`, `s:`, `hg:`, `sg:`, `id:`)
- Refreshed dialogs across the app (comments, acknowledge, downtime, board create, change password, user settings, admin pages)
- Light theme polished: sidebar visibility, checkbox marks, board cards and form contrast
- User data moved out of `local/share/orbvis/` to `$OMD_ROOT/var/orbvis/` (boards, SQLite DB, venv, htdocs) and `$OMD_ROOT/etc/orbvis/` (`.env`). Avoids replicating OrbVis data across remote sites on *Activate Changes*. Existing installs are migrated automatically by `orbvis-setup`
- MKP updates now self-heal — when the bundled version differs from what's installed, OrbVis runs the setup step on its own

### Security

- Textbox content is no longer rendered as HTML (XSS hardening)
- Host and service actions are restricted to admins
- Connection paths and IDs are validated against path traversal
- Board line colors are validated and legacy invalid values are sanitized on load
- Dependency bumps for known CVEs in `python-multipart`, `mako` (via Alembic) and `sanitize-html`

### Bug Fixes

- BI aggregation state now stays correct even when batched state calls return empty
- Settings save bar no longer bleeds through scrolled content
- Settings "modified" indicator no longer flags untouched optional fields
- Number inputs keep your typed digits instead of clamping mid-typing
- Adding a background image no longer shifts existing objects on the board
- Save becomes active again after replacing a background image with the same filename
- Worldmap marker labels are centered under the icon and respect the configured size
- Hover tooltips and edit modal headers show the raw object identifier instead of the label override
- Compatibility with Checkmk 2.5 for service-collection queries
- The backend service starts reliably under OMD with proper liveness checks
- Help tooltips and dropdown arrows render correctly across themes
- Dropdowns stay clickable inside dialogs

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
- Flow board: spread hosts so fan/orbit/row service rings of top-K hosts don't overlap their donut neighbours on zoom-in
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
