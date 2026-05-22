"""Stdlib HS256 JWT — replaces PyJWT.

PyJWT is absent from OMD's site-packages; adding it to the MKP wheelhouse just
for symmetric JWTs isn't worth the dependency. The known JWT pitfalls handled
here (and asserted in tests/test_jwt.py): algorithm-confusion via ``alg: "none"``
or RS256-with-HMAC-secret, non-constant-time signature compare, tampered
payload, expired tokens. Datetime payload claims are converted to Unix
timestamps the same way PyJWT does so tokens stay wire-compatible across the
dependency swap.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import time
from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any


class PyJWTError(Exception):
    """Base class for all JWT errors (name kept for PyJWT-compat catches)."""


class InvalidTokenError(PyJWTError):
    pass


class ExpiredSignatureError(InvalidTokenError):
    pass


class InvalidAlgorithmError(InvalidTokenError):
    pass


_SUPPORTED = frozenset({"HS256"})


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    try:
        return base64.urlsafe_b64decode(data + padding)
    except (ValueError, binascii.Error) as e:
        raise InvalidTokenError("invalid base64url segment") from e


def _to_timestamp(value: Any) -> Any:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return int(value.timestamp())
    return value


def _normalize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(payload)
    for claim in ("exp", "iat", "nbf"):
        if claim in normalized:
            normalized[claim] = _to_timestamp(normalized[claim])
    return normalized


def encode(payload: dict[str, Any], key: str, algorithm: str = "HS256") -> str:
    if algorithm not in _SUPPORTED:
        raise InvalidAlgorithmError(f"unsupported algorithm: {algorithm!r}")
    header = {"alg": algorithm, "typ": "JWT"}
    body = _normalize_payload(payload)
    h = _b64url_encode(json.dumps(header, separators=(",", ":"), sort_keys=True).encode())
    p = _b64url_encode(json.dumps(body, separators=(",", ":"), sort_keys=True).encode())
    signing_input = f"{h}.{p}".encode("ascii")
    secret = key.encode("utf-8")
    sig = hmac.new(secret, signing_input, hashlib.sha256).digest()
    return f"{h}.{p}.{_b64url_encode(sig)}"


def decode(
    token: str,
    key: str,
    algorithms: Iterable[str] | None = None,
) -> dict[str, Any]:
    if algorithms is None:
        raise InvalidAlgorithmError("algorithms must be specified")
    allowed = frozenset(algorithms)
    if not allowed:
        raise InvalidAlgorithmError("algorithms must not be empty")
    # Defense in depth against a caller passing ["none"] or ["RS256"].
    if not allowed.issubset(_SUPPORTED):
        raise InvalidAlgorithmError(f"unsupported algorithm in whitelist: {allowed!r}")

    try:
        h_b64, p_b64, s_b64 = token.split(".")
    except ValueError as e:
        raise InvalidTokenError("malformed token") from e

    try:
        header = json.loads(_b64url_decode(h_b64))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise InvalidTokenError("invalid header") from e
    if not isinstance(header, dict):
        raise InvalidTokenError("header is not an object")

    alg = header.get("alg")
    if not isinstance(alg, str) or alg not in allowed:
        raise InvalidAlgorithmError(f"algorithm {alg!r} not in whitelist")

    signing_input = f"{h_b64}.{p_b64}".encode("ascii")
    secret = key.encode("utf-8")
    expected = hmac.new(secret, signing_input, hashlib.sha256).digest()
    actual = _b64url_decode(s_b64)
    if not hmac.compare_digest(expected, actual):
        raise InvalidTokenError("signature mismatch")

    try:
        payload = json.loads(_b64url_decode(p_b64))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise InvalidTokenError("invalid payload") from e
    if not isinstance(payload, dict):
        raise InvalidTokenError("payload is not an object")

    now = time.time()
    exp = payload.get("exp")
    if exp is not None:
        if not isinstance(exp, (int, float)):
            raise InvalidTokenError("exp must be a number")
        if now >= exp:
            raise ExpiredSignatureError("token expired")
    nbf = payload.get("nbf")
    if nbf is not None:
        if not isinstance(nbf, (int, float)):
            raise InvalidTokenError("nbf must be a number")
        if now < nbf:
            raise InvalidTokenError("token not yet valid")

    return payload
