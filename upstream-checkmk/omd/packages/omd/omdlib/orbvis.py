#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
from pathlib import Path

from omdlib.config_api import Config, PortHook


def write_orbvis_apache_conf(_site_name: str, site_home: Path, config: Config) -> None:
    # Toggle the apache reverse proxy for the OrbVis (Checkmk Maps) backend.
    orbvis_conf = site_home / "etc" / "apache" / "conf.d" / "orbvis.conf"
    if config["ORBVIS"] == "on":
        orbvis_conf.unlink(missing_ok=True)
        os.symlink("../../orbvis/apache.conf", orbvis_conf)
    elif orbvis_conf.is_file():
        orbvis_conf.unlink()


def _write_orbvis_port_conf(site_name: str, site_home: Path, config: Config) -> None:
    if config["ORBVIS"] != "on":
        return
    port = config["ORBVIS_PORT"]
    # The REST API and the Server-Sent-Events state stream are proxied to the
    # loopback daemon. SSE needs unbuffered, long-lived forwarding: flushpackets
    # pushes each event immediately and the long timeout keeps the stream open.
    # (OrbVis uses SSE, not WebSocket, so no Upgrade handling is required.)
    apache_content = f"""\
# Written by ORBVIS_PORT hook
LoadModule proxy_module /omd/sites/{site_name}/lib/apache/modules/mod_proxy.so
LoadModule proxy_http_module /omd/sites/{site_name}/lib/apache/modules/mod_proxy_http.so

ProxyPass "/{site_name}/orbvis/api" "http://[::1]:{port}/api" retry=0 timeout=3600 flushpackets=on
ProxyPassReverse "/{site_name}/orbvis/api" "http://[::1]:{port}/api"
"""
    orbvis_etc = site_home / "etc" / "orbvis"
    orbvis_etc.mkdir(parents=True, exist_ok=True)
    (orbvis_etc / "apache.conf").write_text(apache_content)


ORBVIS_PORT_HOOK = PortHook(
    name="ORBVIS_PORT",
    display_name="OrbVis (Checkmk Maps) backend port",
    default_port=5580,
    activation=_write_orbvis_port_conf,
)
