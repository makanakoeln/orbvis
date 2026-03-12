"""Authentication business logic."""

from __future__ import annotations

import base64
import hashlib
import hmac as _hmac
import logging
import pathlib
import re
import secrets

import bcrypt as _bcrypt

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.schemas.auth import TokenResponse
from app.schemas.user import UserCreate

logger = logging.getLogger(__name__)

# Checkmk usernames: letters, digits, @, dot, hyphen, underscore.
# Validated before use in filesystem paths to prevent path traversal.
_USERNAME_RE = re.compile(r"^[a-zA-Z0-9@._-]+$")

# Languages supported by OrbVis — used when mapping CMK language codes.
_SUPPORTED_LANGUAGES = {"en", "de"}

# Pre-computed bcrypt hash used as a timing dummy when no DB user is found.
# Computing it once at import time avoids an extra ~100 ms bcrypt round on
# every failed login with an unknown username.
_DUMMY_HASH: str = hash_password(secrets.token_hex(16))


def get_cmk_language(username: str) -> str | None:
    """Return the CMK UI language for a user mapped to a supported OrbVis language.

    Returns a language code ('en', 'de', …) if the CMK language is supported,
    None if CMK is not configured or the language is unknown/unsupported.
    Fallback on the caller's side should be 'en'.
    """
    if not settings.checkmk_omd_root or not _USERNAME_RE.match(username):
        return None
    from app.integrations import checkmk as cmk_integration
    if cmk_integration.available:
        raw = cmk_integration.load_user(username).get("language")
    else:
        lang_file = pathlib.Path(settings.checkmk_omd_root) / "var" / "check_mk" / "web" / username / "language.mk"
        raw = lang_file.read_text().strip() if lang_file.is_file() else None
    if not raw:
        return None
    return raw if raw in _SUPPORTED_LANGUAGES else "en"


def get_cmk_theme(username: str) -> str | None:
    """Return the CMK theme for a user.

    Returns 'light', 'dark', or None when CMK_OMD_ROOT is not configured.
    """
    if not settings.checkmk_omd_root or not _USERNAME_RE.match(username):
        return None
    from app.integrations import checkmk as cmk_integration
    if cmk_integration.available:
        raw = cmk_integration.load_user(username).get("ui_theme")
    else:
        # Fallback: read ui_theme.mk directly (plain-text, not a Python expression)
        theme_file = pathlib.Path(settings.checkmk_omd_root) / "var" / "check_mk" / "web" / username / "ui_theme.mk"
        raw = theme_file.read_text().strip() if theme_file.is_file() else None
    # "facelift" → light, "modern-dark" / absent → dark (CMK default)
    return "light" if raw == "facelift" else "dark"


def validate_checkmk_cookie(cookie_value: str) -> str | None:
    """Validate a Checkmk auth cookie and return the username, or None if invalid.

    Cookie format: username:session_id:hmac_hex
    HMAC = HMAC-SHA256(auth_secret, b"username" + b"session_id" + b"serial").hex()
    """
    omd_root = settings.checkmk_omd_root
    if not omd_root:
        logger.warning("SSO: CHECKMK_OMD_ROOT not set, skipping cookie validation")
        return None
    try:
        parts = cookie_value.split(":", 2)
        if len(parts) != 3:
            logger.warning("SSO: cookie has unexpected format (parts=%d)", len(parts))
            return None
        username, session_id, cookie_hash = parts

        # Validate username before using it in a filesystem path.
        # An attacker-controlled username with ".." could traverse outside OMD_ROOT.
        if not _USERNAME_RE.match(username):
            logger.warning("SSO: rejecting cookie with unsafe username: %r", username)
            return None

        secret_path = pathlib.Path(omd_root) / "etc" / "auth.secret"
        if not secret_path.is_file():
            logger.warning("SSO: auth.secret not found at %s", secret_path)
            return None
        secret = secret_path.read_bytes().strip()

        serial_path = pathlib.Path(omd_root) / "var" / "check_mk" / "web" / username / "serial.mk"
        serial = 0
        if serial_path.is_file():
            try:
                serial = int(serial_path.read_text().strip())
            except ValueError:
                logger.warning("SSO: could not parse serial from %s", serial_path)

        msg = f"{username}{session_id}{serial}".encode()
        expected = _hmac.new(key=secret, msg=msg, digestmod=hashlib.sha256).digest().hex()
        if not _hmac.compare_digest(expected, cookie_hash):
            logger.warning("SSO: HMAC mismatch for user %r (serial=%d)", username, serial)
            return None
        return username
    except Exception as e:
        logger.warning("SSO: cookie validation failed: %s", e)
        return None


def _crypt_verify(password: str, hashed: str) -> bool:
    """Verify a password against a crypt(3)-style hash (MD5/APR1/SHA-crypt).

    The ``crypt`` standard-library module was removed in Python 3.13 (PEP 594).
    If it is not available this function returns False and logs a warning so that
    bcrypt and SHA1 htpasswd entries continue to work unaffected.
    Mitigation: migrate htpasswd entries to bcrypt ($2y$) format.
    """
    try:
        import crypt
    except ImportError:
        logger.warning(
            "crypt module is unavailable (removed in Python 3.13+). "
            "MD5/APR1/SHA-crypt htpasswd entries cannot be verified. "
            "Migrate the htpasswd file to bcrypt ($2y$) format."
        )
        return False
    return crypt.crypt(password, hashed) == hashed


def _verify_htpasswd(username: str, password: str) -> bool:
    """Validate credentials against a Checkmk/Apache htpasswd file."""
    htpasswd_path = settings.checkmk_htpasswd
    if not htpasswd_path:
        return False
    p = pathlib.Path(htpasswd_path)
    if not p.is_file():
        return False
    try:
        for line in p.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(":", 1)
            if len(parts) != 2 or parts[0] != username:
                continue
            hashed = parts[1]
            # Apache htpasswd uses SHA1 ({SHA}), bcrypt ($2y$/$2b$),
            # MD5/APR1 ($apr1$), or SHA-crypt ($5$/$6$) via crypt(3).
            try:
                if hashed.startswith("{SHA}"):
                    digest = base64.b64encode(hashlib.sha1(password.encode()).digest()).decode()
                    return f"{{SHA}}{digest}" == hashed
                # bcrypt ($2y$ or $2b$)
                if hashed.startswith("$2y$") or hashed.startswith("$2b$"):
                    return _bcrypt.checkpw(password.encode(), hashed.replace("$2y$", "$2b$").encode())
                # MD5 / APR1 ($apr1$) and SHA-crypt ($5$/$6$) via crypt(3)
                return _crypt_verify(password, hashed)
            except Exception:
                return False
    except Exception as e:
        logger.warning("htpasswd check failed: %s", e)
    return False


async def authenticate_user(db: AsyncSession, username: str, password: str) -> User | None:
    """Return User if credentials are valid, else None.

    Checks orbvis DB first; falls back to Checkmk htpasswd if configured.

    Timing note: verify_password (bcrypt, ~100 ms) is always called – even when no
    DB user is found – to prevent response-timing attacks that enumerate valid usernames.
    """
    result = await db.execute(select(User).where(User.name == username))
    user = result.scalar_one_or_none()

    if user is not None:
        if not user.is_active:
            # Still verify to maintain constant time, then reject.
            verify_password(password, user.password)
            return None
        if verify_password(password, user.password):
            return user
    else:
        # No DB user found. Run a dummy bcrypt check so an attacker cannot infer
        # username existence from the faster code path.
        verify_password(password, _DUMMY_HASH)

    # Checkmk htpasswd fallback
    if _verify_htpasswd(username, password):
        if user is None:
            user = await get_or_create_sso_user(db, username)
        else:
            # Sync admin flag for htpasswd users – only when CHECKMK_OMD_ROOT is configured.
            # Without OMD_ROOT we cannot determine CMK roles, so we preserve the existing flag
            # rather than incorrectly clearing admin status.
            if settings.checkmk_omd_root:
                is_admin = _is_checkmk_admin(username)
                if user.is_admin != is_admin:
                    user.is_admin = is_admin
                    await db.flush()
        return user

    return None


def create_tokens(user: User) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(user.user_id),
        refresh_token=create_refresh_token(user.user_id),
    )


async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    result = await db.execute(select(User).where(User.user_id == user_id))
    return result.scalar_one_or_none()


def _is_checkmk_admin(username: str) -> bool:
    """Check whether a Checkmk user has the 'admin' role."""
    if not settings.checkmk_omd_root:
        logger.warning("CHECKMK_OMD_ROOT not set – cannot determine Checkmk role for %s", username)
        return False
    from app.integrations import checkmk as cmk_integration
    if cmk_integration.available:
        user_data = cmk_integration.load_user(username)
        is_admin = "admin" in user_data.get("roles", [])
        logger.debug("Checkmk role check for %s: roles=%s is_admin=%s", username, user_data.get("roles"), is_admin)
        return is_admin
    # Fallback: read users.mk directly via exec()
    users_mk = pathlib.Path(settings.checkmk_omd_root) / "etc" / "check_mk" / "multisite.d" / "wato" / "users.mk"
    if not users_mk.is_file():
        logger.warning("Checkmk users.mk not found at %s", users_mk)
        return False
    try:
        ns: dict = {"multisite_users": {}}
        exec(compile(users_mk.read_text(encoding="utf-8"), str(users_mk), "exec"), ns)  # noqa: S102
        user_cfg = ns["multisite_users"].get(username, {})
        is_admin = "admin" in user_cfg.get("roles", [])
        logger.debug("Checkmk role check for %s: roles=%s is_admin=%s", username, user_cfg.get("roles"), is_admin)
        return is_admin
    except Exception as e:
        logger.warning("Could not read Checkmk users.mk: %s", e)
        return False


async def get_or_create_sso_user(db: AsyncSession, username: str) -> User:
    """Find existing user by name or create a new one for SSO login.

    Admin status is determined by the user's Checkmk role (mirrors NagVis behaviour).
    Existing users' admin flag is updated on every login in case their role changed.
    """
    is_admin = _is_checkmk_admin(username)

    result = await db.execute(select(User).where(User.name == username))
    user = result.scalar_one_or_none()
    if user is not None:
        # Sync admin flag in case the Checkmk role changed since last login
        if user.is_admin != is_admin:
            user.is_admin = is_admin
            await db.flush()
        return user

    user = User(
        name=username,
        password=hash_password(secrets.token_hex(32)),
        is_active=True,
        is_admin=is_admin,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    logger.info("Created SSO user: %s (admin=%s)", username, is_admin)
    return user


async def create_user(db: AsyncSession, data: UserCreate) -> User:
    user = User(
        name=data.name,
        password=hash_password(data.password),
        is_active=data.is_active,
        is_admin=data.is_admin,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user
