# Installing OrbVis

OrbVis is built primarily for use **inside Checkmk**. It can be installed three ways:

1. **As a Checkmk MKP** (recommended) — runs inside an OMD site, reuses Checkmk
   auth and Livestatus, and shows up in the Checkmk main menu.
2. **Standalone via .deb / .rpm** — systemd service plus reverse proxy.
3. **From source** — for development.

OrbVis is developed and tested mainly on **Ubuntu 24.04**, but supports
every OS that Checkmk itself supports (Ubuntu 22.04/24.04, Debian 12/13,
RHEL 8/9/10, Rocky / AlmaLinux, SUSE 15 SP6/SP7/16). Reports from other
platforms are welcome.

## 1. Checkmk MKP

### Requirements

- Checkmk 2.3, 2.4, 2.5 or 2.6 — pick the matching MKP:
  - `orbvis-cmk-2.3.mkp` (Checkmk 2.3)
  - `orbvis-cmk-2.4.mkp` (Checkmk 2.4)
  - `orbvis-cmk-2.5.mkp` (Checkmk 2.5)
  - `orbvis-cmk-2.6.mkp` (Checkmk 2.6)
- A working OMD site (the default `APACHE_MODE=own` is required —
  `mkp enable` reloads the site Apache).
- Python 3.12 available on the system. OrbVis creates its own venv under
  `$OMD_ROOT/var/orbvis/venv/` using the site's `python3` if it
  is 3.12+, otherwise the first system `python3` on `PATH`.

### Install

```bash
# As root (or with sudo) — install the MKP into the site
omd su <site>
mkp add ~/orbvis-cmk-2.5.mkp
mkp enable orbvis

# Run the post-install setup once
orbvis-setup
```

If you install the MKP via the Checkmk GUI (*Setup → Maintenance →
Extension packages → Upload package*), enabling the package alone is
**not enough** — you still have to run `orbvis-setup` once on the
command line as the site user. The GUI has no way to extract the
frontend bundle, create the venv, register the OMD service or wire up
Apache; that is what `orbvis-setup` does.

```bash
omd su <site>
orbvis-setup
```

`orbvis-setup` will:

- Extract the pre-built frontend bundle to
  `$OMD_ROOT/var/orbvis/htdocs/`
- Create a Python venv at `$OMD_ROOT/var/orbvis/venv/` and install the
  backend
- Seed three demo boards on first install (skipped on upgrade)
- Generate `$OMD_ROOT/etc/orbvis/.env` with a fresh `SECRET_KEY`
  (preserved on upgrade)
- Write an Apache reverse-proxy snippet under
  `$OMD_ROOT/etc/apache/conf.d/orbvis.conf`
- Register an OMD service so `omd start/stop/restart orbvis` works
- Reload Apache and start the OrbVis backend on port 8420 (loopback only)

If `omd status orbvis` shows the service as stopped after setup
finishes (rarely seen on Checkmk 2.3), start it manually:

```bash
omd start orbvis
```

After setup, OrbVis appears as the **OrbVis** entry in the Checkmk main
menu and as a sidebar snapin (*Edit sidebar → OrbVis Boards*). The
proxied URL works as well:

```
https://<host>/<site>/orbvis/
```

Authentication uses your existing Checkmk session — no separate OrbVis
password is set up. See [Permissions & access control](#permissions--access-control)
below for who can see which boards on first login.

### Upgrade

Re-add and re-enable the MKP, then restart the site. The OrbVis init
script compares the installed VERSION against the one shipped in the
new MKP and runs `orbvis-setup` automatically when they differ. User
data (`boards/`, `orbvis.db`, `.env`, `connections.json`) is preserved.

```bash
omd su <site>
mkp disable orbvis
mkp add ~/orbvis-cmk-2.5.mkp     # overwrites the old version
mkp enable orbvis
exit
omd restart <site>                # auto_refresh in init.d/orbvis runs orbvis-setup
```

The same auto-refresh fires when you upload the new MKP through the
Checkmk GUI (*Setup → Maintenance → Extension packages → Upload
package*) and then restart the site. You can still run `orbvis-setup`
manually if you want to refresh immediately without a full site
restart:

```bash
omd su <site> -c orbvis-setup
```

After the upgrade, force-reload the OrbVis tab once in the browser
(`Ctrl+Shift+R`, or `Cmd+Shift+R` on macOS). The browser caches the old
`index.html` and may keep serving the previous JS/CSS bundle until the
cache is bypassed, which surfaces as stale views or unchanged click
behaviour right after the upgrade.

### Uninstall

OrbVis can be removed cleanly at any time — both from the command line
and from the Checkmk GUI. The order matters: always run
`orbvis-setup uninstall` **before** disabling or removing the MKP, so
that the OMD service, Apache snippet and venv are torn down while the
package's hook scripts are still in place.

```bash
omd su <site>
orbvis-setup uninstall   # stops the service, removes apache snippet + venv
mkp disable orbvis
mkp remove orbvis
```

If you prefer the Checkmk GUI (*Setup → Maintenance → Extension
packages*), still run `orbvis-setup uninstall` on the command line
first, then disable and delete the package in the GUI. Disabling or
removing the MKP without running the uninstall step first leaves a
stopped OMD service and a stale Apache snippet behind that you would
have to clean up by hand.

User data is preserved under `$OMD_ROOT/var/orbvis/`
(`boards/`, `orbvis.db`, `connections.json`) and `$OMD_ROOT/etc/orbvis/.env`
so you can re-install later without losing anything. Delete those paths
manually if you want a fully clean removal.

If you installed an earlier OrbVis version that lived under
`$OMD_ROOT/local/share/orbvis/`, `orbvis-setup` automatically migrates
your data to the new layout on next run. Existing `boards/`, `orbvis.db`
and `connections.json` are moved verbatim; the `.env` is moved to
`etc/orbvis/.env`; venv/htdocs/server source are rebuilt in the new
location. The legacy directory is removed once empty.

### Distributed Checkmk setups (central + remote sites)

OrbVis is designed to live on the **central site only** when you run a
distributed Checkmk cluster. It opens Livestatus connections to all
remote sites listed in `etc/check_mk/multisite.d/sites.mk` (same
`MultiSiteConnection` the Checkmk GUI uses), so a single board can mix
hosts and services from any number of remote sites transparently.

**Why nothing OrbVis-related lives under `local/share/orbvis/`.** The
WATO snapshot pushed by *Activate Changes* replicates the entire
`local/` tree to every remote site
(`cmk.gui.watolib.activate_changes.replication_paths`, ident=`local`).
Putting boards, the SQLite DB or the Python venv there would balloon
every snapshot and replicate user data we don't want on remotes.
OrbVis therefore installs to `$OMD_ROOT/var/orbvis/` (data, venv,
htdocs, src) and `$OMD_ROOT/etc/orbvis/` (admin `.env`) — neither path
is in `replication_paths`, so *Activate Changes* leaves OrbVis
untouched.

The only OrbVis files inside `local/` are the three Checkmk GUI bridge
plugins (`local/lib/python3/cmk/gui/plugins/{sidebar,wato}/orbvis_*.py`,
~few KB total). They auto-detect whether OrbVis is installed on the
current site by checking for `$OMD_ROOT/etc/apache/conf.d/orbvis.conf`
— so even after the snapshot pushes the plugins to remotes that don't
run OrbVis, the sidebar snapin renders *"OrbVis is not installed on
this site."* instead of broken links.

Three supported topologies:

- **Central only (default for distributed setups).** OrbVis on the
  master, Livestatus fan-out to all remotes. Users either click into
  the central OrbVis directly (`https://<master>/<site>/orbvis/`) or,
  if a remote site is reachable from the user's browser, can land on
  the master via the Checkmk session cookie (the `etc/auth.secret`
  HMAC is already shared with remotes by Checkmk, so SSO works).
- **Standalone (single site or air-gapped customer remote).** Run
  `orbvis-setup` on that site only. Boards are local; the
  `MultiSiteConnection` falls back to the single-site fast path
  automatically.
- **Hybrid (central + isolated remote with its own OrbVis).** Both
  sites install OrbVis independently — no data is shared between
  them. The next *Activate Changes* leaves both installations alone
  (data sits in `var/`+`etc/`); only the bridge plugins under
  `local/lib/python3/cmk/gui/plugins/...` are pushed from master to
  remote, which is fine because they're auto-detecting and version-
  stable.

## 2. Standalone (.deb / .rpm)

Download the latest `.deb` or `.rpm` from the
[Releases page](https://github.com/makanakoeln/orbvis/releases):

```bash
# Debian / Ubuntu
sudo dpkg -i orbvis_X.Y.Z_amd64.deb

# RHEL / Rocky / SUSE
sudo rpm -i orbvis-X.Y.Z.x86_64.rpm
```

The package only stages files under `/opt/orbvis` and provides the
helper commands `orbvis-install` and `orbvis-setup` in `/usr/bin`.
Pick **one** of the two follow-up steps:

```bash
# A) Standalone — creates the system user, builds the venv,
#    writes /etc/systemd/system/orbvis.service, starts the
#    service, and configures nginx or Apache if present.
orbvis-install

# B) Add to an existing Checkmk / OMD site — wires up the
#    site's Apache and registers an OMD init script so
#    `omd start/stop orbvis` works.
orbvis-setup <site-name>
```

Both helpers must be invoked as a normal user (not via `sudo`); they
prompt for sudo internally where root is required.

After `orbvis-install` the standalone service is up:

```bash
sudo systemctl status orbvis
```

### First login (standalone)

On first start OrbVis seeds an `admin` user with a random password and prints
it once to the service log. Recover it via:

```bash
sudo journalctl -u orbvis --no-pager | grep 'Default admin'
```

Log in at the proxied URL, change the password, then create additional users
in *Admin → Users*. See [Permissions & access control](#permissions--access-control)
below for the role model.

## 3. From source

Clone the repository and run one of the helpers depending on the target.

### Standalone

```bash
./install.sh                # install
./install.sh remove         # uninstall (user data is kept)
```

Installs to `/opt/orbvis`, creates the `orbvis` system user, builds the
frontend, writes `/etc/systemd/system/orbvis.service`, and configures
nginx or Apache automatically if either is present. Requirements:
Python 3.12+, Node.js 18+, systemd, sudo.

### Into an existing Checkmk / OMD site

```bash
./install_cmk.sh <site-name>          # install
./install_cmk.sh <site-name> remove   # uninstall
```

Wires up the site's Apache and registers an OMD init script so
`omd start/stop orbvis` works.

For day-to-day backend/frontend hacking (hot-reload, no system
install) see the [README → Development](../README.md#development).

## 4. Docker Compose

Use the bundled `docker-compose.yml` for evaluation or single-host
deployments without OMD or system-wide install:

```bash
./bootstrap.sh              # one-time: generates .env, ensures data/ dirs exist
docker compose up --build
```

- Frontend: `http://localhost:8741`
- API docs: `http://localhost:8742/api/docs`

The default admin password is in the backend container log:

```bash
docker compose logs orbvis | grep 'Default admin'
```

State (boards, users, `backends.json`) persists in `./data/` on the
host, so `docker compose down` does not lose data.

## Permissions & access control

OrbVis has two distinct permission paths depending on how it is deployed.

### Inside an OMD site (MKP install)

Authentication and authorization are delegated to Checkmk. The MKP ships
WATO permissions under *Setup → Users → Roles & permissions → OrbVis*:

| Permission             | Default roles | Meaning                                                |
| ---------------------- | ------------- | ------------------------------------------------------ |
| `orbvis.use`           | admin, user   | Required to access OrbVis at all                       |
| `orbvis.view_all`      | admin, user   | Read access to every board                             |
| `orbvis.edit_all`      | admin         | Create / modify / delete boards                        |
| `orbvis.configure`     | admin         | Access general settings, connections, images           |
| `orbvis.view_<board>`  | admin, user   | Per-board read access (registered dynamically)         |
| `orbvis.edit_<board>`  | admin         | Per-board write access (registered dynamically)        |

What this means on first login:

- **Checkmk admin role** — sees and edits everything. OrbVis sets
  `is_admin=True` automatically based on the Checkmk role.
- **Checkmk user role** — sees all boards by default; cannot edit.
- **Checkmk guest role** (or any custom role without `orbvis.use`) — has no
  OrbVis access. Grant the relevant permissions in WATO.

To restrict a role to specific boards, remove `orbvis.view_all` and grant
the per-board `orbvis.view_<board>` permissions instead. The same applies to
edit access. OrbVis' own role management is *not* used in OMD mode — Checkmk
is the single source of truth.

### Standalone (.deb / .rpm / Docker)

OrbVis manages users, roles and permissions itself. Two roles are seeded on
first start:

- **Administrators** — `map/view/*`, `map/edit/*`, `user/edit/*`
- **Viewers** — `map/view/*`

Permissions follow the legacy NagVis `mod / act / obj` triple. `obj` is
either `*` (all boards) or a specific board name. Manage users and roles in
*Admin → Users* / *Admin → Roles*.

The default `admin` user is created on first start with a random password,
printed once to the service log (see [First login (standalone)](#first-login-standalone)
above).

## Production hardening

### Single-worker deployment (current limitation)

OrbVis maintains its JWT refresh-token blocklist **in process memory**. In a
multi-worker setup (`uvicorn --workers 4`), a logout on one worker does not
invalidate refresh tokens on the others until they expire naturally.

**Until a Redis-backed blocklist lands, run OrbVis with a single worker.** The
default in both the OMD init script and the standalone systemd unit is one
worker — please don't increase it without a follow-up plan for the blocklist.

For higher throughput, the bottleneck is almost always Livestatus / Checkmk,
not OrbVis itself. Real installs with hundreds of concurrent clients have
been comfortable on a single uvicorn worker.

### Reverse proxy / TLS

Both the OMD-MKP and standalone install paths put OrbVis behind Apache or
nginx. Make sure TLS is enabled on the frontend host — OrbVis itself listens
only on `127.0.0.1`.

### CORS

`ALLOWED_ORIGINS` defaults to `http://localhost:5173` for development. In
production behind a reverse proxy, set it to your real frontend URL via
`backend/.env` (or, on OMD, `$OMD_ROOT/etc/orbvis/.env`):

```
ALLOWED_ORIGINS=https://monitoring.example.com
```

A wrong value will silently drop browser requests; check the browser console
if frontend calls fail with CORS errors.

### Logs

- OMD: `$OMD_ROOT/var/log/orbvis.log`
- Standalone (systemd): `journalctl -u orbvis`
- Docker: container stdout (`docker compose logs orbvis`)

Set `LOG_LEVEL=INFO` or `WARNING` in production. `DEBUG` is helpful for
troubleshooting but will log a lot of state-refresh chatter.
