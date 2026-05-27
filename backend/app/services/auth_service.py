"""Authentication business logic — stdlib sqlite3, no ORM."""

from __future__ import annotations

import ast
import asyncio
import base64
import hashlib
import hmac as _hmac
import logging
import pathlib
import re
import secrets
import sqlite3
from typing import Any

import bcrypt as _bcrypt

from app.core import _jwt
from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)
from app.integrations import checkmk as cmk_integration
from app.models.permission import Permission
from app.models.role import Role
from app.models.user import User
from app.schemas.auth import TokenResponse
from app.schemas.user import UserCreate

logger = logging.getLogger(__name__)


def _hmac_sha256_hex(secret: bytes, msg: bytes) -> str:
    return _hmac.new(key=secret, msg=msg, digestmod=hashlib.sha256).digest().hex()


# Checkmk usernames: letters, digits, @, dot, hyphen, underscore.
# Validated before use in filesystem paths to prevent path traversal.
_USERNAME_RE = re.compile(r"^[a-zA-Z0-9@._-]+$")
_SUPPORTED_LANGUAGES = {"en", "de"}

# Timing dummy: derived deterministically from SECRET_KEY so every worker uses
# the *same* pre-image and bcrypt-verify cost matches a real user's path.
_DUMMY_HASH: str = hash_password(
    hashlib.sha256(f"orbvis-dummy|{settings.secret_key}".encode()).hexdigest()
)

_USER_COLS = "user_id, name, password, is_active, is_admin, must_change_password, theme, language"


def _row_to_user(row: sqlite3.Row) -> User:
    return User(
        user_id=row["user_id"],
        name=row["name"],
        password=row["password"],
        is_active=bool(row["is_active"]),
        is_admin=bool(row["is_admin"]),
        must_change_password=bool(row["must_change_password"]),
        theme=row["theme"],
        language=row["language"],
    )


def _load_roles_for_user(conn: sqlite3.Connection, user_id: int) -> list[Role]:
    role_rows = conn.execute(
        """
        SELECT r.role_id, r.name
        FROM roles r
        JOIN users2roles u2r ON u2r.role_id = r.role_id
        WHERE u2r.user_id = ?
        """,
        (user_id,),
    ).fetchall()
    if not role_rows:
        return []
    roles = {r["role_id"]: Role(role_id=r["role_id"], name=r["name"]) for r in role_rows}
    placeholders = ",".join(["?"] * len(roles))
    perm_rows = conn.execute(
        f"""
        SELECT p.perm_id, p.mod, p.act, p.obj, r2p.role_id
        FROM permissions p
        JOIN roles2perms r2p ON r2p.perm_id = p.perm_id
        WHERE r2p.role_id IN ({placeholders})
        """,  # nosec B608 — placeholders are "?" markers, not user input
        tuple(roles.keys()),
    ).fetchall()
    for row in perm_rows:
        roles[row["role_id"]].permissions.append(
            Permission(perm_id=row["perm_id"], mod=row["mod"], act=row["act"], obj=row["obj"])
        )
    return list(roles.values())


def _fetch_user(conn: sqlite3.Connection, where: str, params: tuple[Any, ...]) -> User | None:
    # `where` is hand-written by the caller (not user input); the f-string is
    # safe and the placeholders bind real parameters.
    row = conn.execute(
        f"SELECT {_USER_COLS} FROM users WHERE {where}",  # nosec B608
        params,
    ).fetchone()
    if row is None:
        return None
    user = _row_to_user(row)
    user.roles = _load_roles_for_user(conn, user.user_id)
    return user


def get_cmk_language(username: str) -> str | None:
    """Return the CMK UI language for a user mapped to a supported OrbVis language.

    Returns a language code ('en', 'de', …) if the CMK language is supported,
    None if CMK is not configured or the language is unknown/unsupported.
    Fallback on the caller's side should be 'en'.
    """
    if not settings.checkmk_omd_root or not _USERNAME_RE.match(username):
        return None

    if cmk_integration.available:
        raw_value = cmk_integration.load_user(username).get("language")
        raw = raw_value if isinstance(raw_value, str) else None
    else:
        lang_file = (
            pathlib.Path(settings.checkmk_omd_root)
            / "var"
            / "check_mk"
            / "web"
            / username
            / "language.mk"
        )
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

    if cmk_integration.available:
        raw = cmk_integration.load_user(username).get("ui_theme")
    else:
        theme_file = (
            pathlib.Path(settings.checkmk_omd_root)
            / "var"
            / "check_mk"
            / "web"
            / username
            / "ui_theme.mk"
        )
        raw = theme_file.read_text().strip() if theme_file.is_file() else None
    return "light" if raw == "facelift" else "dark"


def validate_checkmk_cookie(cookie_value: str) -> str | None:
    """Validate a Checkmk auth cookie and return the username, or None if invalid.

    Cookie format: username:session_id:hmac_hex
    HMAC = HMAC-SHA256(auth_secret, b"username" + b"session_id" + b"serial").hex()

    The HMAC alone is *not* enough: Checkmk sets the cookie immediately after
    the password step, before WebAuthn/TOTP, so we additionally require that
    the persisted session has reached the fully-logged-in state.
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

        root = pathlib.Path(omd_root)
        secret_path = root / "etc" / "auth.secret"
        if not secret_path.is_file():
            logger.warning("SSO: auth.secret not found at %s", secret_path)
            return None
        secret = secret_path.read_bytes()

        serial_path = root / "var" / "check_mk" / "web" / username / "serial.mk"
        serial = 0
        if serial_path.is_file():
            try:
                serial = int(serial_path.read_text().strip())
            except ValueError:
                logger.warning("SSO: could not parse serial from %s", serial_path)

        msg_25 = f"{username}:{session_id}:{serial}".encode()
        msg_24 = f"{username}{session_id}{serial}".encode()
        if not (
            _hmac.compare_digest(_hmac_sha256_hex(secret, msg_25), cookie_hash)
            | _hmac.compare_digest(_hmac_sha256_hex(secret, msg_24), cookie_hash)
        ):
            logger.warning("SSO: HMAC mismatch for user %r (serial=%d)", username, serial)
            return None

        if not _is_session_fully_authenticated(root, username, session_id):
            logger.warning(
                "SSO: rejecting cookie for %r — session %s has not completed 2FA / login",
                username,
                session_id[:8] + "…",
            )
            return None
        return username
    except Exception as e:
        logger.warning("SSO: cookie validation failed: %s", e)
        return None


def _is_session_fully_authenticated(omd_root: pathlib.Path, username: str, session_id: str) -> bool:
    """Return True iff the CMK session has finished every login step.

    Mirrors the gate ``cmk.gui.wsgi.applications.utils.ensure_authentication``
    applies inside the GUI. The on-disk session-info layout differs between
    Checkmk versions — 2.3/2.4 use the boolean fields ``logged_out`` and
    ``two_factor_completed``, 2.5+ collapsed both into a ``session_state``
    state machine where only ``"logged_in"`` is fully authenticated.

    Conservative on failure: if the session can't be located or parsed, we
    return False so an attacker can't ride a stale or evicted cookie.
    """
    info = _load_session_info(omd_root, username, session_id)
    if info is None:
        return False

    # CMK 2.5+: explicit state machine wins when present.
    state = info.get("session_state")
    if isinstance(state, str):
        return state == "logged_in"

    # CMK 2.3/2.4: boolean flags. Logged-out blocks first; 2FA gate only
    # applies when the user actually has 2FA credentials registered.
    if info.get("logged_out") is True:
        return False
    if _user_has_two_factor_configured(omd_root, username):
        return info.get("two_factor_completed") is True
    return True


def _load_session_info(
    omd_root: pathlib.Path, username: str, session_id: str
) -> dict[str, Any] | None:
    """Parse ``var/check_mk/web/<user>/session_info.mk`` and pick one session.

    CMK writes the file with ``repr({k: asdict(v) for ...})`` in every
    supported version, so ``ast.literal_eval`` round-trips it safely.
    """
    path = omd_root / "var" / "check_mk" / "web" / username / "session_info.mk"
    try:
        raw = path.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeDecodeError):
        return None
    if not raw:
        return None
    try:
        sessions = ast.literal_eval(raw)
    except (ValueError, SyntaxError):
        logger.warning("SSO: could not parse %s", path)
        return None
    if not isinstance(sessions, dict):
        return None
    info = sessions.get(session_id)
    return info if isinstance(info, dict) else None


def _user_has_two_factor_configured(omd_root: pathlib.Path, username: str) -> bool:
    """Mirror of CMK's ``is_two_factor_login_enabled`` (2.3 – 2.6+).

    The credentials file holds a dict with ``webauthn_credentials`` and
    ``totp_credentials`` mappings; the user is 2FA-enabled iff either has at
    least one entry.
    """
    path = omd_root / "var" / "check_mk" / "web" / username / "two_factor_credentials.mk"
    try:
        raw = path.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeDecodeError):
        return False
    if not raw:
        return False
    try:
        creds = ast.literal_eval(raw)
    except (ValueError, SyntaxError):
        return False
    if not isinstance(creds, dict):
        return False
    return bool(creds.get("webauthn_credentials") or creds.get("totp_credentials"))


def user_has_two_factor_enabled(username: str) -> bool:
    """Whether the Checkmk user has a second factor (WebAuthn/TOTP) registered.

    Password-only form logins must be refused for these users: OrbVis cannot run
    Checkmk's WebAuthn/TOTP challenge itself, so a 2FA user has to enter through
    the SSO cookie path, which enforces the full Checkmk login state machine via
    :func:`_is_session_fully_authenticated`. Without this gate the form login is
    a 2FA bypass — the htpasswd fallback in :func:`authenticate_user` accepts a
    bare password regardless of registered factors.

    Returns False in standalone deployments where no OMD root is configured.
    """
    omd_root = settings.checkmk_omd_root
    if not omd_root or not _USERNAME_RE.match(username):
        return False
    return _user_has_two_factor_configured(pathlib.Path(omd_root), username)


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
            try:
                if hashed.startswith("{SHA}"):
                    digest = base64.b64encode(
                        hashlib.sha1(password.encode(), usedforsecurity=False).digest()
                    ).decode()
                    return f"{{SHA}}{digest}" == hashed
                if hashed.startswith("$2y$") or hashed.startswith("$2b$"):
                    return _bcrypt.checkpw(
                        password.encode(), hashed.replace("$2y$", "$2b$").encode()
                    )
                return _crypt_verify(password, hashed)
            except Exception:
                return False
    except Exception as e:
        logger.warning("htpasswd check failed: %s", e)
    return False


async def authenticate_user(conn: sqlite3.Connection, username: str, password: str) -> User | None:
    """Return User if credentials are valid, else None.

    Checks orbvis DB first; falls back to Checkmk htpasswd if configured.

    Timing note: verify_password (bcrypt, ~100 ms) is always called – even when
    no DB user is found – to prevent response-timing attacks that enumerate
    valid usernames.
    """
    user = await asyncio.to_thread(_fetch_user, conn, "name = ?", (username,))

    if user is not None:
        if not user.is_active:
            # Still verify to maintain constant time, then reject.
            verify_password(password, user.password)
            return None
        if verify_password(password, user.password):
            return user
    else:
        verify_password(password, _DUMMY_HASH)

    # Checkmk htpasswd fallback
    if _verify_htpasswd(username, password):
        if user is None:
            user = await get_or_create_sso_user(conn, username)
        elif settings.checkmk_omd_root:
            is_admin = _is_checkmk_admin(username)
            if user.is_admin != is_admin:
                await asyncio.to_thread(_set_admin_flag, conn, user.user_id, is_admin)
                user.is_admin = is_admin
        return user

    return None


def _set_admin_flag(conn: sqlite3.Connection, user_id: int, is_admin: bool) -> None:
    conn.execute("UPDATE users SET is_admin = ? WHERE user_id = ?", (1 if is_admin else 0, user_id))


def create_tokens(user: User) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(user.user_id),
        refresh_token=create_refresh_token(user.user_id),
    )


async def get_user_by_id(conn: sqlite3.Connection, user_id: int) -> User | None:
    return await asyncio.to_thread(_fetch_user, conn, "user_id = ?", (user_id,))


async def authenticate_bearer_token(conn: sqlite3.Connection, token: str) -> User | None:
    """Decode a bearer JWT, verify it's an active access token, load the user.

    Shared by FastAPI HTTP deps and the SSE handshake so both paths reject
    non-access tokens, blocklisted tokens, and inactive users identically.
    """
    from app.core.security import decode_token, is_token_blocked

    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            return None
        user_id = int(str(payload["sub"]))
        jti = str(payload.get("jti", ""))
    except (_jwt.PyJWTError, KeyError, ValueError):
        return None

    if jti and is_token_blocked(jti):
        return None

    user = await get_user_by_id(conn, user_id)
    if user is None or not user.is_active:
        return None
    return user


def _is_checkmk_admin(username: str) -> bool:
    if not settings.checkmk_omd_root:
        logger.warning("CHECKMK_OMD_ROOT not set – cannot determine Checkmk role for %s", username)
        return False

    if cmk_integration.available:
        user_data = cmk_integration.load_user(username)
        roles = user_data.get("roles", [])
        is_admin = isinstance(roles, list) and "admin" in roles
        logger.debug(
            "Checkmk role check for %s: roles=%s is_admin=%s",
            username,
            roles,
            is_admin,
        )
        return is_admin
    users_mk = (
        pathlib.Path(settings.checkmk_omd_root)
        / "etc"
        / "check_mk"
        / "multisite.d"
        / "wato"
        / "users.mk"
    )
    if not users_mk.is_file():
        logger.warning("Checkmk users.mk not found at %s", users_mk)
        return False
    try:
        multisite_users = cmk_integration.exec_mk_file(users_mk, {"multisite_users": {}})[
            "multisite_users"
        ]
        user_cfg = multisite_users.get(username, {}) if isinstance(multisite_users, dict) else {}
        roles = user_cfg.get("roles", []) if isinstance(user_cfg, dict) else []
        is_admin = isinstance(roles, list) and "admin" in roles
        logger.debug(
            "Checkmk role check for %s: roles=%s is_admin=%s",
            username,
            roles,
            is_admin,
        )
        return is_admin
    except Exception as e:
        logger.warning("Could not read Checkmk users.mk: %s", e)
        return False


def _insert_user_sync(
    conn: sqlite3.Connection,
    name: str,
    password: str,
    is_active: bool,
    is_admin: bool,
    must_change_password: bool = False,
) -> int:
    cursor = conn.execute(
        """
        INSERT INTO users (name, password, is_active, is_admin, must_change_password)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            name,
            password,
            1 if is_active else 0,
            1 if is_admin else 0,
            1 if must_change_password else 0,
        ),
    )
    user_id = cursor.lastrowid
    assert user_id is not None
    return user_id


async def get_or_create_sso_user(conn: sqlite3.Connection, username: str) -> User:
    is_admin = _is_checkmk_admin(username)

    user = await asyncio.to_thread(_fetch_user, conn, "name = ?", (username,))
    if user is not None:
        if user.is_admin != is_admin:
            await asyncio.to_thread(_set_admin_flag, conn, user.user_id, is_admin)
            user.is_admin = is_admin
        return user

    def _create() -> int:
        return _insert_user_sync(
            conn,
            name=username,
            password=hash_password(secrets.token_hex(32)),
            is_active=True,
            is_admin=is_admin,
        )

    user_id = await asyncio.to_thread(_create)
    logger.info("Created SSO user: %s (admin=%s)", username, is_admin)
    user = await get_user_by_id(conn, user_id)
    assert user is not None
    return user


async def create_user(conn: sqlite3.Connection, data: UserCreate) -> User:
    def _create() -> int:
        return _insert_user_sync(
            conn,
            name=data.name,
            password=hash_password(data.password),
            is_active=data.is_active,
            is_admin=data.is_admin,
            must_change_password=data.must_change_password,
        )

    user_id = await asyncio.to_thread(_create)
    user = await get_user_by_id(conn, user_id)
    assert user is not None
    return user
