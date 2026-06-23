# Merge-time edits

Most of `upstream-checkmk/` mirrors **whole files** that rsync into
`~/git/checkmk/` 1:1. This file lists the edits that touch **existing** Checkmk
core files and therefore cannot be shipped as a mirror — they must be applied by
hand (or by a patch) at merge time. New mirror files are noted for context.

## OMD glue — backend daemon (workstream C4)

New mirror files (rsync as-is):

- `omd/packages/omd/omdlib/orbvis.py` — apache reverse-proxy conf writer +
  `ORBVIS_PORT_HOOK` (modeled on `omdlib/jaeger.py`). OrbVis is SSE-only (no
  WebSocket), so the proxy needs only `flushpackets`/long timeout, no Upgrade.
- `omd/packages/check_mk/ORBVIS`, `omd/packages/check_mk/ORBVIS_PORT` —
  `omd config` hook metadata (modeled on `AGENT_RECEIVER*`).
- `packages/cmk-orbvis-backend/skel/etc/logrotate.d/orbvis-backend`,
  `.../skel/etc/init.d/orbvis-backend`, `.../skel/etc/orbvis-backend/gunicorn.conf.py`
  — daemon runtime (in the package).

Edits to existing files:

- `omd/packages/omd/omdlib/config_hooks.py`:
  - import `ORBVIS_PORT_HOOK, write_orbvis_apache_conf` from `omdlib.orbvis`.
  - `_HOOK_CHOICES`: add `"ORBVIS": [("on", "enable"), ("off", "disable")]`.
  - `_HOOK_DEPENDS`: add `"ORBVIS_PORT": lambda c: c.get("ORBVIS") == "on"`.
  - `_DEFAULT_HOOKS`: add `"ORBVIS": lambda _edition: "on"` (NagVis successor;
    Cloud edition excludes the package entirely — see E).
  - `PORT_HOOKS`: append `ORBVIS_PORT_HOOK`.
  - `_MIGRATED_ACTIVATION`: add `"ORBVIS": write_orbvis_apache_conf`.
- `omd/packages/check_mk/BUILD` (or the relevant skel-tar filegroup): include the
  `ORBVIS` / `ORBVIS_PORT` hooks.

Still to finalize at merge time (need an OMD site to verify):

- Per-site secret for the SSE stream tickets: provision `etc/orbvis/orbvis.env`
  with a generated `SECRET_KEY` (e.g. on first `init.d start`).
- Data dir `var/orbvis/maps` (the daemon's `MAPS_DIR`) — add as a skel dir.
- The site Apache path layout vs. the GUI-served SPA shell (see C1): the proxy
  currently forwards `/<site>/orbvis/api`; confirm the SPA bundle + other dynamic
  daemon routes (images, map backgrounds) once the GUI page layout is fixed.
- SSE through OMD's double-Apache: SSE is plain chunked HTTP (no Upgrade), so the
  outer system Apache should pass it through; verify no buffering/timeout cutoff.

## GUI Monitor/Setup integration (workstream C1)

New mirror files (rsync as-is): `cmk/gui/orbvis/{_maps,_orbvis_auth,_pages,
_monitor_menu,_setup,__init__}.py` (the sidebar snapin `_orbvis_maps.py` and
`_boards.py` were removed). Frontend bundle is loaded from
`web_dir/htdocs/cmk-orbvis-frontend/.manifest.json`.

Edits to existing files:

- `cmk/gui/community_registration.py`:
  - import `orbvis` and call `orbvis.register(permission_section_registry,
    permission_registry, page_registry, main_module_topic_registry,
    main_module_registry)` (new signature — no snapin).
  - **Monitor topic composition:** Checkmk has no plugin hook to add a topic to
    the existing Monitor menu, so compose the `view_menu_topics` callback passed
    to `sidebar.register(...)`. Replace
    `view_menu_topics=sidebar.default_view_menu_topics` with a small wrapper:
    ```python
    def _view_menu_topics(user_permissions):
        return [
            *sidebar.default_view_menu_topics(user_permissions),
            *orbvis.orbvis_monitor_topics(user_permissions),
        ]
    ```
    and pass `view_menu_topics=_view_menu_topics`. The same composition is needed
    in the nonfree edition registrations (`cmk.gui.nonfree.{pro,ultimate,
    ultimatemt}.registration`) — internal tree.
- `cmk/gui/orbvis/BUILD`: complete the `deps` for the new imports (see the NOTE
  in that file) — Bazel-validated at merge.

To verify at merge (built site): page `check_mk/orbvis.py` renders the SPA shell,
manifest bundle loads, `window.__ORBVIS_BASE__` injected; Monitor shows a "Maps"
topic listing permitted maps; Setup shows a "Maps" module; `IconNames`
(topic_visualization/dashboard/save_dashboard), the `MainModuleTopic.icon_name`
and the registry membership in `test_registration.py` resolve. The page handler's
`make_header(...)` call mirrors `cmk/gui/message.py`.

## Build / edition wiring (workstream E)

- `cmk/gui/BUILD`, `omd/BUILD` edition `select()`s (pkg_tar + skel.permissions),
  `packages/BUILD`, `pnpm-workspace.yaml`, `cmk/ccc/version.py`
  (`edition_supports_maps`), `cmk/gui/community_registration.py` + nonfree
  registration, `tests/unit/.../test_snapins.py`, a `.werks/<id>` entry,
  leaflet in the monorepo `MODULE.bazel`/`pnpm-lock.yaml`. Detailed in the plan
  file and filled in when E is executed.
