# Installing OrbVis

OrbVis can be installed three ways:

1. **As a Checkmk MKP** (recommended for Checkmk users) — runs inside an OMD site,
   reuses Checkmk auth and Livestatus.
2. **Standalone via .deb / .rpm** — systemd service plus reverse proxy.
3. **From source** — for development.

## 1. Checkmk MKP

### Requirements

- Checkmk 2.3, 2.4 (use `orbvis-X.Y.Z-cmk2.3.mkp`) — *or* 2.5+ (use
  `orbvis-X.Y.Z-cmk2.5.mkp`).
- A working OMD site that already has Apache enabled (`omd config` →
  `APACHE_MODE=own`).
- Python 3.12 available on the system. OrbVis creates its own venv under
  `$OMD_ROOT/local/share/orbvis/venv/` using the site's `python3` if it
  is 3.12+, otherwise the first system `python3` on `PATH`.

### Install

```bash
# As root (or with sudo) — install the MKP into the site
omd su <site>
mkp add ~/orbvis-X.Y.Z-cmk2.3.mkp
mkp enable orbvis

# Run the post-install setup once
orbvis-setup
```

`orbvis-setup` will:

- Extract the pre-built frontend bundle to
  `$OMD_ROOT/local/share/orbvis/htdocs/`
- Create a Python venv and install the backend
- Seed three demo boards on first install (skipped on upgrade)
- Generate `.env` with a fresh `SECRET_KEY` (preserved on upgrade)
- Write an Apache reverse-proxy snippet under
  `$OMD_ROOT/etc/apache/conf.d/orbvis.conf`
- Register an OMD service so `omd start/stop/restart orbvis` works
- Reload Apache and start the OrbVis backend on port 8420 (loopback only)

OrbVis is then reachable at:

```
https://<host>/<site>/orbvis/
```

The default admin password is printed once on first start. Recover it via:

```bash
tail -n 200 $OMD_ROOT/var/log/orbvis.log | grep 'Default admin'
```

### Upgrade

Re-add and re-enable the MKP, then run `orbvis-setup` again. User data
(`boards/`, `orbvis.db`, `.env`, `backends.json`) is preserved.

### Uninstall

```bash
orbvis-setup uninstall
mkp disable orbvis
mkp remove orbvis
```

User data is kept under `$OMD_ROOT/local/share/orbvis/`. Remove it
manually if you no longer need it.

## 2. Standalone (.deb / .rpm)

Download the latest `.deb` or `.rpm` from the
[Releases page](https://github.com/makanakoeln/orbvis/releases):

```bash
# Debian / Ubuntu
sudo dpkg -i orbvis_X.Y.Z_amd64.deb

# RHEL / Rocky / SUSE
sudo rpm -i orbvis-X.Y.Z.x86_64.rpm
```

The package installs to `/opt/orbvis`, registers a systemd unit, and
configures nginx or Apache automatically if either is present.

```bash
sudo systemctl status orbvis
sudo journalctl -u orbvis --no-pager | grep 'Default admin'
```

## 3. From source

See the [README](../README.md#development) for a development setup.

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
`backend/.env` (or, on OMD, `$OMD_ROOT/local/share/orbvis/.env`):

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
