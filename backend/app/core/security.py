"""JWT and password hashing utilities."""

from datetime import UTC, datetime, timedelta
from threading import Lock
from uuid import uuid4

import bcrypt

from app.core import _jwt
from app.core.config import settings

# In-memory blocklist — lives per process. With multiple uvicorn workers a
# logout on worker A leaves the token usable on workers B…N until expiry.
# Move to a shared store (DB / Redis) when multi-worker becomes a goal.
_blocklist: dict[str, datetime] = {}
_blocklist_lock = Lock()


def _prune_blocklist() -> None:
    now = datetime.now(UTC)
    with _blocklist_lock:
        expired = [jti for jti, exp in _blocklist.items() if exp <= now]
        for jti in expired:
            del _blocklist[jti]


def blocklist_token(jti: str, expiry: datetime) -> None:
    _prune_blocklist()
    with _blocklist_lock:
        _blocklist[jti] = expiry


def is_token_blocked(jti: str) -> bool:
    # Prune on read too — a long-running process with rare logouts otherwise
    # never clears expired entries.
    _prune_blocklist()
    with _blocklist_lock:
        return jti in _blocklist


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def create_access_token(subject: str | int, expires_delta: timedelta | None = None) -> str:
    if expires_delta is None:
        # Late import to avoid a security ↔ settings_service ↔ schemas cycle.
        from app.services import settings_service

        expires_delta = timedelta(
            minutes=settings_service.get_effective_access_token_expire_minutes()
        )
    expire = datetime.now(UTC) + expires_delta
    payload = {"sub": str(subject), "exp": expire, "type": "access", "jti": uuid4().hex}
    return _jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def create_refresh_token(subject: str | int) -> str:
    expire = datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days)
    payload = {"sub": str(subject), "exp": expire, "type": "refresh", "jti": uuid4().hex}
    return _jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_token(token: str) -> dict[str, object]:
    return _jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
