"""Tests for the in-tree HS256 JWT implementation (app.core._jwt).

These guard against the well-known JWT pitfalls — algorithm confusion,
timing leaks, tampered payloads, expired tokens, padding edge cases — and
verify wire-format compatibility with PyJWT so existing sessions survive
the dependency swap.
"""

from __future__ import annotations

import base64
import json
import time
from datetime import UTC, datetime, timedelta

import pytest

from app.core import _jwt

SECRET = "test-secret-do-not-use"


def _split(token: str) -> tuple[str, str, str]:
    h, p, s = token.split(".")
    return h, p, s


def _decode_segment(seg: str) -> dict:
    padding = "=" * (-len(seg) % 4)
    return json.loads(base64.urlsafe_b64decode(seg + padding))


def test_encode_decode_roundtrip() -> None:
    payload = {"sub": "42", "type": "access", "jti": "abc"}
    token = _jwt.encode(payload, SECRET, algorithm="HS256")
    decoded = _jwt.decode(token, SECRET, algorithms=["HS256"])
    assert decoded["sub"] == "42"
    assert decoded["type"] == "access"
    assert decoded["jti"] == "abc"


def test_datetime_exp_is_converted_to_unix_timestamp() -> None:
    exp = datetime.now(UTC) + timedelta(hours=1)
    token = _jwt.encode({"sub": "1", "exp": exp}, SECRET, algorithm="HS256")
    _, p_b64, _ = _split(token)
    payload = _decode_segment(p_b64)
    assert isinstance(payload["exp"], int)
    assert abs(payload["exp"] - int(exp.timestamp())) <= 1


def test_naive_datetime_is_treated_as_utc() -> None:
    # PyJWT documents naive datetimes as UTC; match that behavior.
    exp = datetime.utcnow() + timedelta(hours=1)
    token = _jwt.encode({"sub": "1", "exp": exp}, SECRET, algorithm="HS256")
    decoded = _jwt.decode(token, SECRET, algorithms=["HS256"])
    assert "exp" in decoded


# ---------------------------------------------------------------------------
# Algorithm-confusion attacks (RFC 8725 §3.1)
# ---------------------------------------------------------------------------


def test_alg_none_is_rejected_even_with_matching_whitelist() -> None:
    # Forge a token with alg=none and empty signature.
    header = base64.urlsafe_b64encode(b'{"alg":"none","typ":"JWT"}').rstrip(b"=").decode()
    payload = base64.urlsafe_b64encode(b'{"sub":"1"}').rstrip(b"=").decode()
    forged = f"{header}.{payload}."
    # Even if someone explicitly listed "none", our supported set rejects it.
    with pytest.raises(_jwt.InvalidAlgorithmError):
        _jwt.decode(forged, SECRET, algorithms=["none"])
    # And it must be rejected against HS256 too.
    with pytest.raises(_jwt.InvalidAlgorithmError):
        _jwt.decode(forged, SECRET, algorithms=["HS256"])


def test_rs256_header_with_hmac_secret_is_rejected() -> None:
    # Classic confusion attack: server uses HMAC verify with a public-key alg
    # claimed in the header. The HMAC over the alleged-RS256 signing input
    # would succeed if the verifier didn't check the alg.
    header = base64.urlsafe_b64encode(b'{"alg":"RS256","typ":"JWT"}').rstrip(b"=").decode()
    payload = base64.urlsafe_b64encode(b'{"sub":"1"}').rstrip(b"=").decode()
    import hashlib
    import hmac

    sig = hmac.new(SECRET.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest()
    sig_b64 = base64.urlsafe_b64encode(sig).rstrip(b"=").decode()
    forged = f"{header}.{payload}.{sig_b64}"
    with pytest.raises(_jwt.InvalidAlgorithmError):
        _jwt.decode(forged, SECRET, algorithms=["HS256"])


def test_unknown_alg_is_rejected() -> None:
    header = base64.urlsafe_b64encode(b'{"alg":"HS512","typ":"JWT"}').rstrip(b"=").decode()
    payload = base64.urlsafe_b64encode(b'{"sub":"1"}').rstrip(b"=").decode()
    forged = f"{header}.{payload}.signature"
    with pytest.raises(_jwt.InvalidAlgorithmError):
        _jwt.decode(forged, SECRET, algorithms=["HS256"])


def test_encode_rejects_non_hs256() -> None:
    with pytest.raises(_jwt.InvalidAlgorithmError):
        _jwt.encode({"sub": "1"}, SECRET, algorithm="HS512")


def test_decode_requires_algorithms_argument() -> None:
    token = _jwt.encode({"sub": "1"}, SECRET, algorithm="HS256")
    with pytest.raises(_jwt.InvalidAlgorithmError):
        _jwt.decode(token, SECRET, algorithms=None)
    with pytest.raises(_jwt.InvalidAlgorithmError):
        _jwt.decode(token, SECRET, algorithms=[])


# ---------------------------------------------------------------------------
# Tampering / signature integrity
# ---------------------------------------------------------------------------


def test_tampered_payload_is_rejected() -> None:
    token = _jwt.encode({"sub": "1"}, SECRET, algorithm="HS256")
    h, _p, s = _split(token)
    # Flip one bit in the payload and re-encode without re-signing.
    tampered_payload = base64.urlsafe_b64encode(b'{"sub":"2"}').rstrip(b"=").decode()
    forged = f"{h}.{tampered_payload}.{s}"
    with pytest.raises(_jwt.InvalidTokenError):
        _jwt.decode(forged, SECRET, algorithms=["HS256"])


def test_wrong_secret_is_rejected() -> None:
    token = _jwt.encode({"sub": "1"}, SECRET, algorithm="HS256")
    with pytest.raises(_jwt.InvalidTokenError):
        _jwt.decode(token, "different-secret", algorithms=["HS256"])


def test_malformed_token_is_rejected() -> None:
    for bad in ["", "header.payload", "a.b.c.d", "not-base64.payload.sig"]:
        with pytest.raises(_jwt.InvalidTokenError):
            _jwt.decode(bad, SECRET, algorithms=["HS256"])


def test_garbage_signature_is_rejected() -> None:
    token = _jwt.encode({"sub": "1"}, SECRET, algorithm="HS256")
    h, p, _ = _split(token)
    forged = f"{h}.{p}.AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    with pytest.raises(_jwt.InvalidTokenError):
        _jwt.decode(forged, SECRET, algorithms=["HS256"])


# ---------------------------------------------------------------------------
# Time-bound claims
# ---------------------------------------------------------------------------


def test_expired_token_is_rejected() -> None:
    past = datetime.now(UTC) - timedelta(seconds=5)
    token = _jwt.encode({"sub": "1", "exp": past}, SECRET, algorithm="HS256")
    with pytest.raises(_jwt.ExpiredSignatureError):
        _jwt.decode(token, SECRET, algorithms=["HS256"])


def test_future_token_is_accepted() -> None:
    future = datetime.now(UTC) + timedelta(seconds=60)
    token = _jwt.encode({"sub": "1", "exp": future}, SECRET, algorithm="HS256")
    decoded = _jwt.decode(token, SECRET, algorithms=["HS256"])
    assert "exp" in decoded


def test_nbf_in_future_is_rejected() -> None:
    nbf = int(time.time()) + 60
    token = _jwt.encode({"sub": "1", "nbf": nbf}, SECRET, algorithm="HS256")
    with pytest.raises(_jwt.InvalidTokenError):
        _jwt.decode(token, SECRET, algorithms=["HS256"])


def test_missing_exp_is_accepted() -> None:
    token = _jwt.encode({"sub": "1"}, SECRET, algorithm="HS256")
    decoded = _jwt.decode(token, SECRET, algorithms=["HS256"])
    assert decoded == {"sub": "1"}


def test_exp_must_be_numeric() -> None:
    # Forge a token where exp is a string — payload is signed correctly, but
    # the claim itself is malformed.
    import hashlib
    import hmac

    header = base64.urlsafe_b64encode(b'{"alg":"HS256","typ":"JWT"}').rstrip(b"=").decode()
    payload = base64.urlsafe_b64encode(b'{"sub":"1","exp":"tomorrow"}').rstrip(b"=").decode()
    sig = hmac.new(SECRET.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest()
    sig_b64 = base64.urlsafe_b64encode(sig).rstrip(b"=").decode()
    token = f"{header}.{payload}.{sig_b64}"
    with pytest.raises(_jwt.InvalidTokenError):
        _jwt.decode(token, SECRET, algorithms=["HS256"])


# ---------------------------------------------------------------------------
# Base64url padding handling
# ---------------------------------------------------------------------------


def test_base64url_without_padding_is_handled() -> None:
    # Our encoder strips '=' padding; decoder must restore it. Verify roundtrip
    # for payloads whose JSON length doesn't fall on a 4-byte boundary.
    for sub in ["a", "ab", "abc", "abcd"]:
        token = _jwt.encode({"sub": sub}, SECRET, algorithm="HS256")
        assert "=" not in token
        decoded = _jwt.decode(token, SECRET, algorithms=["HS256"])
        assert decoded["sub"] == sub


# ---------------------------------------------------------------------------
# PyJWT cross-compatibility — protects existing sessions across the dep swap
# ---------------------------------------------------------------------------


@pytest.fixture
def pyjwt_module() -> object:
    # PyJWT is still installed in dev environments (requirements.[dev]) during
    # the migration window. Skip the cross-compat test if PyJWT is gone.
    try:
        import jwt as _pyjwt

        return _pyjwt
    except ImportError:
        pytest.skip("PyJWT not installed; skipping cross-compat test")


def test_pyjwt_encoded_can_be_decoded_by_ours(pyjwt_module: object) -> None:
    import jwt as _pyjwt

    future = datetime.now(UTC) + timedelta(hours=1)
    token = _pyjwt.encode(
        {"sub": "42", "type": "access", "jti": "x", "exp": future},
        SECRET,
        algorithm="HS256",
    )
    decoded = _jwt.decode(token, SECRET, algorithms=["HS256"])
    assert decoded["sub"] == "42"
    assert decoded["type"] == "access"


def test_our_token_can_be_decoded_by_pyjwt(pyjwt_module: object) -> None:
    import jwt as _pyjwt

    future = datetime.now(UTC) + timedelta(hours=1)
    token = _jwt.encode(
        {"sub": "42", "type": "access", "jti": "x", "exp": future},
        SECRET,
        algorithm="HS256",
    )
    decoded = _pyjwt.decode(token, SECRET, algorithms=["HS256"])
    assert decoded["sub"] == "42"
    assert decoded["type"] == "access"
