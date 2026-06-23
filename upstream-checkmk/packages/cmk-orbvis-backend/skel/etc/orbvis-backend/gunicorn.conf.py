#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Gunicorn configuration for the OrbVis (Checkmk Maps) backend daemon.

The OrbVis backend keeps live state in-process (the SSE state push runs from a
single background task and a shared connection registry), so it MUST run as a
single worker. We use the uvicorn ASGI worker; the long-lived SSE connections
need a generous (effectively disabled) request timeout so the worker is not
recycled mid-stream.
"""

import os

workers = 1
worker_class = "uvicorn.workers.UvicornWorker"

# 0 disables the silence-timeout watchdog -- async workers heartbeat, and our
# SSE responses stay open for minutes.
timeout = 0
graceful_timeout = 30

omd_root = os.environ.get("OMD_ROOT", "")
log_dir = os.path.join(omd_root, "var/log/orbvis-backend")
os.makedirs(log_dir, exist_ok=True)

accesslog = os.path.join(log_dir, "access.log")
errorlog = os.path.join(log_dir, "error.log")
loglevel = "info"

# Not needed and conflicts with omd backup (mirrors agent-receiver).
control_socket_disable = True
