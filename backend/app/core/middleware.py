"""ASGI middlewares that don't belong in any single router.

Kept as bare ASGI classes (not Starlette ``BaseHTTPMiddleware``) so header
inspection can short-circuit without materialising a Request object.
"""

from __future__ import annotations

from collections.abc import Iterable
from urllib.parse import urlsplit

from starlette.types import ASGIApp, Message, Receive, Scope, Send


def _host_only(value: str) -> str:
    """First entry of an X-Forwarded-Host chain, port stripped, lowercased."""
    first = value.split(",", 1)[0].strip()
    if first.startswith("["):
        end = first.find("]")
        return first[: end + 1].lower() if end >= 0 else first.lower()
    return first.rsplit(":", 1)[0].lower() if ":" in first else first.lower()


def is_same_origin(origin: str, raw_headers: Iterable[tuple[bytes, bytes]]) -> bool:
    """True when ``Origin``'s host matches the request's authoritative host.

    Reverse-proxy aware: ``X-Forwarded-Host`` wins over ``Host`` because the
    latter typically carries the upstream port (``127.0.0.1:8422``) once the
    request lands at the backend. ASGI scope header names are lowercased
    bytes per the ASGI spec, so no case folding is needed here.
    """
    origin_host = urlsplit(origin).hostname
    if not origin_host:
        return False
    fwd = ""
    host = ""
    for name, value in raw_headers:
        if name == b"x-forwarded-host" and not fwd:
            fwd = value.decode("latin-1")
        elif name == b"host" and not host:
            host = value.decode("latin-1")
        if fwd and host:
            break
    if fwd and _host_only(fwd) == origin_host:
        return True
    return bool(host) and _host_only(host) == origin_host


class SecurityHeadersMiddleware:
    """Add security-related HTTP headers to every response."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers += [
                    (b"x-content-type-options", b"nosniff"),
                    (b"x-frame-options", b"SAMEORIGIN"),
                    (b"referrer-policy", b"strict-origin-when-cross-origin"),
                    (b"x-xss-protection", b"1; mode=block"),
                ]
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, send_with_headers)


class MethodOverrideMiddleware:
    """Tunnel PATCH/PUT/DELETE through POST via X-HTTP-Method-Override header.

    Some reverse proxies (e.g. OMD/Checkmk Apache) block non-GET/POST methods.
    The frontend sends POST with X-HTTP-Method-Override: PATCH (etc.) and this
    middleware rewrites the ASGI scope method before routing, so all existing
    FastAPI routes work unchanged.
    """

    _ALLOWED = frozenset(("PATCH", "PUT", "DELETE"))

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and scope["method"] == "POST":
            headers = {k.lower(): v for k, v in scope.get("headers", [])}
            override = headers.get(b"x-http-method-override", b"").decode().upper()
            if override in self._ALLOWED:
                scope = {**scope, "method": override}
        await self.app(scope, receive, send)


class CSRFOriginMiddleware:
    """Reject state-changing Cookie-authed requests from unexpected origins.

    Bearer-token requests are CSRF-immune (browsers do not send the token
    automatically). Cookie-authenticated state-changing requests, however,
    CAN be triggered by a malicious third-party origin via a forged form or
    fetch. We defend by requiring the Origin header to match one of the
    configured allowed_origins for any POST/PUT/PATCH/DELETE that does not
    carry an Authorization: Bearer header.

    Paths excluded: /api/v1/auth/login (pre-auth; no session yet) and
    /api/v1/auth/sso (Checkmk session cookie establishes the auth).
    """

    _STATE_CHANGING = frozenset(("POST", "PUT", "PATCH", "DELETE"))
    _EXEMPT_PATHS = frozenset(("/api/v1/auth/login", "/api/v1/auth/sso"))

    def __init__(self, app: ASGIApp, allowed_origins: list[str]) -> None:
        self.app = app
        self._allowed = frozenset(allowed_origins)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] not in self._STATE_CHANGING:
            await self.app(scope, receive, send)
            return
        path = scope.get("path", "")
        if path in self._EXEMPT_PATHS or not path.startswith("/api/"):
            await self.app(scope, receive, send)
            return

        headers = {k.lower(): v for k, v in scope.get("headers", [])}
        auth_hdr = headers.get(b"authorization", b"")
        if auth_hdr.startswith(b"Bearer "):
            # Bearer tokens are not sent automatically by browsers → no CSRF risk.
            await self.app(scope, receive, send)
            return
        if not headers.get(b"cookie"):
            # No ambient credentials → the request body is the only auth source
            # and a forged form on another origin cannot synthesise it. This
            # includes API clients hitting /api/v1/auth/refresh with a body.
            await self.app(scope, receive, send)
            return

        origin = headers.get(b"origin", b"").decode("latin-1")
        if origin and (origin in self._allowed or is_same_origin(origin, scope.get("headers", []))):
            await self.app(scope, receive, send)
            return

        # Reject: missing or unexpected Origin on a cookie-authed mutation.
        await send(
            {
                "type": "http.response.start",
                "status": 403,
                "headers": [(b"content-type", b"application/json")],
            }
        )
        await send(
            {
                "type": "http.response.body",
                "body": b'{"detail":"Origin not allowed for this operation"}',
            }
        )
