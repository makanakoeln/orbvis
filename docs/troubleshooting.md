# Troubleshooting

Common problems and how to diagnose them. If your case is not covered,
please open a [GitHub issue](https://github.com/makanakoeln/orbvis/issues)
with the relevant logs.

## OMD / MKP install

### `orbvis-setup` says "MKP library not found at …"

The `mkp enable orbvis` step did not unpack the `lib/` payload to
`$OMD_ROOT/local/lib/orbvis/`. Re-run:

```bash
mkp disable orbvis
mkp enable orbvis
ls $OMD_ROOT/local/lib/orbvis/   # should contain server.tar.gz, htdocs.tar.gz
orbvis-setup
```

### Apache says "mod_proxy not found" / API requests get 404

`orbvis-setup` looks for `mod_proxy.so` in:

- `$OMD_ROOT/lib/apache/modules/` (CMK 2.4+ bundled)
- `/usr/lib/apache2/modules/` (Debian/Ubuntu)
- `/usr/lib64/httpd/modules/` (RHEL/Rocky)
- `/usr/lib/httpd/modules/`

If none of these exist on your system, install the OS package
(`apt install libapache2-mod-proxy-html` on Debian/Ubuntu;
`dnf install mod_proxy` on RHEL family) and re-run `orbvis-setup`.

### `omd start orbvis` reports "OK" but the API returns 502

The backend started but immediately crashed. Check
`$OMD_ROOT/var/log/orbvis.log` for a Python traceback. Most common
causes:

- **Wrong Python version**: OrbVis requires Python 3.12+.
  `omd su <site>; python3 --version`. If your site's Python is
  older, see *Python 3.12 not available* below.
- **Database lock**: another process is holding `orbvis.db`. Stop
  any leftover `uvicorn` processes (`pkill -f orbvis`) and retry.
- **Bad `.env`**: a missing or malformed `SECRET_KEY` makes the
  backend refuse to start in production. Re-running `orbvis-setup`
  rewrites `.env` and preserves an existing `SECRET_KEY` if valid.

### Python 3.12 not available

Older OMD images may ship Python 3.11. OrbVis tries `$OMD_ROOT/bin/python3`
first, then any `python3` on `PATH`. Install a newer Python via
your distribution's backports / the `deadsnakes` PPA:

```bash
# Debian / Ubuntu
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt install python3.12 python3.12-venv

# Then point orbvis-setup at it
PYTHON3=/usr/bin/python3.12 orbvis-setup
```

(`PYTHON3` env var override is honoured by `orbvis-setup`.)

### Login works, but the home screen is empty

No backends are configured, so no boards have any state to show.
*Admin → Backends → Add* and point it at your Livestatus socket
(`$OMD_ROOT/tmp/run/live` for an OMD site).

### Login fails with "invalid credentials" but the password is right

If you are using Checkmk SSO, verify:

- `CHECKMK_OMD_ROOT` in `.env` points at the correct site root
- The Checkmk auth cookie is being sent (browser dev-tools → Network
  → request headers → `Cookie:` should contain `auth_<site>`)
- `$OMD_ROOT/etc/auth.secret` is readable by the OMD site user

For htpasswd-only auth, run `htpasswd -bv $OMD_ROOT/etc/htpasswd <user>
<password>` to verify the hash format is one OrbVis supports (SHA1,
bcrypt, APR1, SHA-crypt — md5crypt is **not** supported).

## Standalone (.deb / .rpm)

### `systemctl status orbvis` shows "failed"

```bash
sudo journalctl -u orbvis --no-pager -n 200
```

Look for the first ERROR line. Common causes are the same as the OMD
list above (Python version, DB lock, bad .env).

### nginx / Apache returns 502 Bad Gateway

Check that the backend is actually listening:

```bash
ss -ltnp | grep 8420   # standalone uses 8420 by default
```

If nothing is bound, the backend is not running — see the systemd logs.

If something is bound, the reverse-proxy config probably points at the
wrong port. The standalone installer writes its config with the port it
chose; manual edits can drift. Re-run `orbvis-install` to regenerate.

## Frontend / browser

### "WebSocket connection to … failed"

- The reverse proxy must forward `/api/v1/ws/...` with `Upgrade` and
  `Connection: Upgrade` headers. The OMD MKP and standalone installers
  both write a working config; if you customised the proxy, verify the
  WS-upgrade rules.
- The OrbVis backend rejects WS connections from origins not in
  `ALLOWED_ORIGINS`. Production: set this to your real frontend URL.

### Boards load but states never update

The WebSocket connected but auth failed silently. Browser console will
show a close frame with code 4401. Confirm the access token is fresh —
log out and log in again to rotate.

### Real-time updates stop after a few minutes

Some reverse proxies idle-timeout WebSockets after 60 seconds. OrbVis
sends a ping every 30 s, but check your proxy timeout (nginx
`proxy_read_timeout`, Apache `ProxyTimeout`) — bump it to at least 120.

## Imports / migration

### `cfg_importer.py` says "unknown gadget_url"

The legacy map references a custom gadget that is not in OrbVis'
known-gadget list. The object is imported as a plain icon. To restore
the gadget, edit the JSON and switch `mode` to `gauge` / `bar` and add
a `gadget_*` config — or open an issue if you think the gadget should
be supported out of the box.

### Imported boards look "shifted" compared to NagVis

NagVis and OrbVis both use pixel coordinates, but background images
sometimes have different intrinsic resolutions. Check the board's
background image dimensions in OrbVis — if it differs from the NagVis
size, either replace the image or use the edit mode to nudge objects.

## Performance

### Backend CPU is high

Check `state_service` metrics in `$OMD_ROOT/var/log/orbvis.log`. If
state-fetch durations are climbing, the bottleneck is almost always
Livestatus. Look at `omd su <site>; livedump --stats` to see whether
the Checkmk core is keeping up.

### Browser is slow on a board with > 500 objects

The static / flow renderers tested up to ~1000 objects on a modern
laptop. Above that, the SVG layer count starts to hurt. Splitting one
large board into several smaller, linked boards is usually the right
move; "one board = 1500 hosts" is rarely a useful view in practice.

## Last resort

If nothing here helps, please file an issue with:

- OrbVis version (`cat $OMD_ROOT/local/lib/orbvis/VERSION`)
- Checkmk version (if applicable)
- Install method
- Last 200 lines of the relevant log
- Browser console output for frontend bugs

We respond fastest to issues that we can reproduce locally.
