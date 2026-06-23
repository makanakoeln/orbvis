# cmk-orbvis-backend

The OrbVis ("Checkmk Maps") FastAPI backend, packaged as a site-local daemon
(agent-receiver model). It serves the Maps REST API plus the live
WebSocket/SSE state push; the site Apache reverse-proxies `/<site>/orbvis` to
it on the loopback interface.

## Generated, not hand-edited

`cmk/orbvis_backend/` is generated from the standalone backend (`backend/app/`
in the orbvis repo) by `scripts/sync-upstream-backend.sh`. Do not edit it by
hand -- change `backend/app/` and re-run the sync. The transform:

- remaps absolute imports `app.` -> `cmk.orbvis_backend.`,
- disambiguates the geo-tile module (`api/v1/maps.py` -> `map_tiles.py`) so the
  board->map rename can turn the boards CRUD into the `maps` resource,
- renames the OrbVis "board" domain term to "map",
- prepends the Checkmk GPLv2 header.

Run `scripts/sync-upstream-backend.sh --check` for a drift check.

## Single process

The daemon MUST run as a single worker: live state (the WebSocket/SSE push and
connection registry) lives in-process. See `skel/etc/orbvis-backend/gunicorn.conf.py`.

## Auth

Authentication runs exclusively through the Checkmk session -- there is no own
login. (The standalone SQLite/JWT auth paths are still present but gated off at
runtime via `CHECKMK_OMD_ROOT`; stripping them is a later cleanup.)

## Open / merge-time

- The Bazel `BUILD` follows the agent-receiver pattern but must be validated in
  the Checkmk monorepo.
- The `CONFIG_ORBVIS` / `CONFIG_ORBVIS_PORT` omd hooks, the rc.d/logrotate
  wiring and the Apache WebSocket/SSE proxy live in the omd glue (workstream C4).
- Per-site secret + data-dir provisioning (`etc/orbvis/orbvis.env`,
  `var/orbvis/maps`) is finalized with the omd glue.
