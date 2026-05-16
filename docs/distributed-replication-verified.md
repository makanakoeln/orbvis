# Distributed setup — WATO replication audit (2026-05-15)

Verifies that OrbVis paths sit on the correct side of CMK's WATO `replication_paths`
list so an Activate Changes from a master to N remotes does the right thing.

## Replication paths registered by Checkmk (verified against master)

Source: `cmk/gui/watolib/activate_changes.py:273-396`. Synced from master to
every remote on Activate Changes:

| Path | Type |
|---|---|
| `etc/check_mk/conf.d/wato` | DIR |
| `etc/check_mk/multisite.d/wato` | DIR |
| `etc/check_mk/...htpasswd` | FILE |
| `etc/check_mk/password_store.secret` | FILE |
| `etc/check_mk/auth.serials` | FILE |
| `etc/check_mk/stored_passwords` | FILE |
| `var/check_mk/web` | DIR |
| `var/check_mk/packages`, `var/check_mk/disabled_packages`, `var/check_mk/packages_local` | DIR |
| **`local`** | DIR |
| `etc/check_mk/conf.d/distributed_wato.mk` | FILE |
| `etc/omd` | DIR |
| `var/rabbitmq/...` | DIR |
| `var/check_mk/wato/frozen_aggregations` | DIR |
| `etc/check_mk/conf.d/wato/topology` | DIR |
| topology settings | FILE |
| `etc/check_mk/apache.d/wato` | DIR |

## OrbVis paths — where they sit and why

| Path | Replicated? | Reason |
|---|---|---|
| `local/lib/python3/cmk/gui/plugins/sidebar/orbvis_boards.py` | **yes** (`local/`) | KB-sized bridge plugin. Auto-detects via `etc/apache/conf.d/orbvis.conf` and renders "OrbVis is not installed on this site" when the host doesn't run a local backend. |
| `local/lib/python3/cmk/gui/plugins/wato/orbvis_menu.py` | **yes** (`local/`) | Same auto-detect, hides the main-menu entry on remotes without OrbVis. |
| `local/lib/python3/cmk/gui/plugins/wato/orbvis_permissions.py` | **yes** (`local/`) | Permission stubs only — file-system reads protected by `try/except`. |
| `var/orbvis/boards/` | no | Per-site user data. |
| `var/orbvis/images/` | no | Per-site user uploads. |
| `var/orbvis/orbvis.db` | no | Per-site SQLite (sessions, users). |
| `var/orbvis/connections.json` | no | Per-site monitoring connections. |
| `var/orbvis/settings.json` | no | Per-site global settings. |
| `var/orbvis/tiles/` | no | Per-site OSM tile cache (large). |
| `var/orbvis/htdocs/` | no | Per-site frontend bundle. |
| `var/orbvis/cmk_plugins/` | no | (No longer used — replaced by the direct copy in `local/lib/python3/...` above.) |
| `var/orbvis/venv/` | no | Per-site Python virtualenv. |
| `var/orbvis/src/` | no | Per-site backend source. |
| `etc/orbvis/.env` | no | Per-site `SECRET_KEY`, `BACKEND_PORT`. |
| `etc/init.d/orbvis` | no | Per-site OMD init script. |
| `etc/apache/conf.d/orbvis.conf` | no | Per-site Apache vhost — also the install marker. |
| `var/log/orbvis.log` | no | Per-site runtime log. |

## Migration from legacy `local/share/orbvis/`

Up to 0.2.0, OrbVis installed everything under `local/share/orbvis/`. That tree
is part of `local/` and gets pushed via Activate Changes — for a 300-remote
distributed setup, every Activate Changes would have copied `orbvis.db`, the
htdocs bundle, the Python venv and the OSM tile cache to every remote.

`install_cmk.sh`/`make_mkp.sh` migrate on every run (idempotent):

- Moves: `boards`, `images`, `orbvis.db`, `connections.json`, `backends.json`,
  `settings.json`, `tiles`, `.env` (latter to `etc/orbvis/`)
- Deletes: `htdocs`, `venv`, `src`, `cmk_plugins`, `VERSION`, `CHANGELOG.md`
  (disposable, rebuilt by the same install run)
- Sweeps post-migration leftovers when the destination already exists, so the
  `local/share/orbvis/` directory ends up empty and gets `rmdir`'d
- Sweeps the direct-written legacy plugins from a previous MKP install
  (`local/lib/python3/cmk/gui/plugins/{sidebar,wato}/orbvis_*.py`) before
  re-installing them — same path, but the install owns those files now.

## Bridge plugin auto-detect contract

A WATO replication push lands the plugin files on every remote, regardless of
whether OrbVis is installed there. To avoid broken nav/sidebar entries on
remotes that don't run an OrbVis backend, each plugin checks
`etc/apache/conf.d/orbvis.conf` at import time:

```python
_LOCAL_INSTALL_MARKER = pathlib.Path(os.environ.get("OMD_ROOT", "")) \
    / "etc" / "apache" / "conf.d" / "orbvis.conf"

def _is_local_install() -> bool:
    return _LOCAL_INSTALL_MARKER.is_file()
```

- `orbvis_boards.py` (sidebar snapin) renders "OrbVis is not installed on this
  site" instead of the boards list.
- `orbvis_menu.py` (main-menu entry) returns an empty topic list, suppressing
  the menu button entirely.
- `orbvis_permissions.py` declares the permission section unconditionally —
  safe even on a remote, no UI side effects.

`etc/apache/conf.d/orbvis.conf` is written only by `install_cmk.sh` /
`orbvis-setup`. It sits **outside** every replication path, so a master's
configuration cannot impersonate it on remotes.

## Verified on ZWEIFUENF (2026-05-15)

```
local/lib/python3/cmk/gui/plugins/sidebar/orbvis_boards.py   ✓ would replicate
local/lib/python3/cmk/gui/plugins/wato/orbvis_menu.py        ✓ would replicate
local/lib/python3/cmk/gui/plugins/wato/orbvis_permissions.py ✓ would replicate
var/orbvis/{boards,images,orbvis.db,connections.json,...}    ✓ stays local
etc/orbvis/.env                                              ✓ stays local
local/share/orbvis/                                          ✓ migrated away (gone)
```

## Limitations

- The MKP bundle itself (when installed via `mkp add`) lands in
  `var/check_mk/packages/orbvis` — which **is** in `replication_paths`. So the
  MKP file gets pushed to remotes; a few MB. The *extracted* state lives in
  `var/orbvis/` and stays local. Bundle-only propagation is an upstream
  Checkmk behaviour, no leakage of user data.
- Bridge plugin version drift across master + isolated-remote-with-its-own-
  OrbVis: if the two installs differ, the master's plugin version wins after
  Activate Changes. Plugins only do filesystem checks + static URL strings,
  so they're stable across minor versions, but a major OrbVis bump should
  coincide across both ends.
