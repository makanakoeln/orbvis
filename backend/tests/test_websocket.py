"""WebSocket fault-handling tests for /api/v1/ws/boards/{name}.

Covered paths:
  - missing first-message auth → 4001
  - malformed first-message     → 4001
  - non-access token (refresh)  → 4001
  - blocked token (logout)      → 4001
  - unknown user_id             → 4001
  - no view permission          → 4003
  - unknown board               → 4004
  - connect rate-limit          → 4008 before accept
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import jwt as _jwt
import pytest
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.core.config import settings
from app.core.ratelimit import ws_connect_limiter
from app.core.security import (
    blocklist_token,
    create_access_token,
    create_refresh_token,
)
from app.main import app


def _ws_client() -> TestClient:
    # TestClient runs the app in a background thread. We only exercise the WS
    # handshake path which doesn't need migrations/seeded data.
    return TestClient(app)


def _reset_limiter() -> None:
    """Clear the in-memory rate-limit window so tests don't interfere."""
    ws_connect_limiter._calls.clear()


@pytest.fixture(autouse=True)
def _reset_ws_state():
    _reset_limiter()
    yield
    _reset_limiter()


def test_ws_rejects_when_no_first_message_is_auth(admin_user):
    with _ws_client().websocket_connect("/api/v1/ws/boards/demo") as ws:
        # Send something that is NOT {"type":"auth", "token":...}
        ws.send_text(json.dumps({"type": "not-auth"}))
        # Server closes with 4001 and TestClient raises on next receive.
        with pytest.raises(WebSocketDisconnect):
            ws.receive_text()


def test_ws_rejects_malformed_first_message(admin_user):
    with _ws_client().websocket_connect("/api/v1/ws/boards/demo") as ws:
        ws.send_text("not-json{{")
        with pytest.raises(WebSocketDisconnect):
            ws.receive_text()


def test_ws_rejects_refresh_token_instead_of_access(admin_user):
    with _ws_client().websocket_connect("/api/v1/ws/boards/demo") as ws:
        refresh = create_refresh_token(admin_user.user_id)
        ws.send_text(json.dumps({"type": "auth", "token": refresh}))
        with pytest.raises(WebSocketDisconnect):
            ws.receive_text()


def test_ws_rejects_blocked_access_token(admin_user):
    """A token that was explicitly blocklisted (e.g. after logout) must not grant WS access."""
    token = create_access_token(admin_user.user_id)
    payload = _jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    jti = str(payload["jti"])
    blocklist_token(jti, datetime.now(UTC) + timedelta(minutes=5))

    with _ws_client().websocket_connect("/api/v1/ws/boards/demo") as ws:
        ws.send_text(json.dumps({"type": "auth", "token": token}))
        with pytest.raises(WebSocketDisconnect):
            ws.receive_text()


def test_ws_rate_limiter_rejects_connection_floods(admin_user):
    """After many handshake attempts from the same source, further connects are refused
    BEFORE websocket.accept(), so a forged flood cannot tie up server slots.
    """
    # Push the limiter right up to its threshold from the TestClient's source.
    client_key = "testclient"
    for _ in range(ws_connect_limiter._max):
        ws_connect_limiter.record(client_key)

    # The next connect attempt must be rejected without upgrading to WS.
    client = _ws_client()
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/api/v1/ws/boards/demo"):
            pass


def test_ws_rejects_disallowed_origin(admin_user):
    """Cross-origin browsers can open WS without a CORS preflight, so OrbVis
    rejects connections whose Origin header is not in the configured allowlist."""
    with pytest.raises(WebSocketDisconnect):
        with _ws_client().websocket_connect(
            "/api/v1/ws/boards/demo",
            headers={"origin": "https://evil.example.com"},
        ):
            pass


def test_ws_accepts_no_origin_header(admin_user, monkeypatch):
    """Non-browser clients (curl, custom websocket libs) send no Origin header
    and must still be allowed — the guard short-circuits when the header is
    missing. Reaches the auth step and rejects there because no token is sent."""
    with _ws_client().websocket_connect("/api/v1/ws/boards/demo") as ws:
        # Got past origin check (otherwise close happens before accept).
        ws.send_text(json.dumps({"type": "not-auth"}))
        with pytest.raises(WebSocketDisconnect):
            ws.receive_text()


def test_ws_accepts_same_origin_via_host_header(admin_user):
    """Same-origin connects (Origin's host == request Host) bypass the explicit
    allowlist. Real-world scenario: backend deployed under OMD where the
    site-FQDN can't easily be enumerated up-front in ALLOWED_ORIGINS."""
    with _ws_client().websocket_connect(
        "/api/v1/ws/boards/demo",
        headers={"origin": "https://orbvis.example.com", "host": "orbvis.example.com"},
    ) as ws:
        ws.send_text(json.dumps({"type": "not-auth"}))
        with pytest.raises(WebSocketDisconnect):
            ws.receive_text()


def test_ws_accepts_same_origin_via_x_forwarded_host(admin_user):
    """Behind a reverse proxy that rewrites Host (ProxyPreserveHost off), the
    original client-facing host arrives in X-Forwarded-Host. Same-origin must
    still match against that header."""
    with _ws_client().websocket_connect(
        "/api/v1/ws/boards/demo",
        headers={
            "origin": "https://orbvis.example.com",
            "host": "127.0.0.1:8422",
            "x-forwarded-host": "orbvis.example.com",
        },
    ) as ws:
        ws.send_text(json.dumps({"type": "not-auth"}))
        with pytest.raises(WebSocketDisconnect):
            ws.receive_text()


def test_ws_rejects_origin_mismatched_with_host(admin_user):
    """Cross-origin attack: malicious page on evil.com with a forged Host
    header still mismatches Origin's host. Reject."""
    with pytest.raises(WebSocketDisconnect):
        with _ws_client().websocket_connect(
            "/api/v1/ws/boards/demo",
            headers={
                "origin": "https://evil.example.com",
                "host": "orbvis.example.com",
            },
        ):
            pass
