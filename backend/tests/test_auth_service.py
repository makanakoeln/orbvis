"""Tests for authentication service functions."""

from __future__ import annotations

import base64
import hashlib
import hmac as _hmac

import bcrypt
import pytest

from app.services.auth_service import (
    _verify_htpasswd,
    authenticate_user,
    get_cmk_language,
    get_or_create_sso_user,
    user_has_two_factor_enabled,
    validate_checkmk_cookie,
)

# ---------------------------------------------------------------------------
# _verify_htpasswd
# ---------------------------------------------------------------------------


def _write_htpasswd(path, username: str, password: str, scheme: str = "bcrypt") -> None:
    if scheme == "sha1":
        digest = base64.b64encode(
            hashlib.sha1(password.encode(), usedforsecurity=False).digest()
        ).decode()
        hashed = f"{{SHA}}{digest}"
    else:
        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=4)).decode()
    path.write_text(f"{username}:{hashed}\n", encoding="utf-8")


def test_verify_htpasswd_sha1_correct(tmp_path, monkeypatch):
    htpasswd = tmp_path / "htpasswd"
    _write_htpasswd(htpasswd, "user1", "secret", scheme="sha1")
    monkeypatch.setattr("app.core.config.settings.checkmk_htpasswd", str(htpasswd))
    monkeypatch.setattr("app.services.auth_service.settings.checkmk_htpasswd", str(htpasswd))
    assert _verify_htpasswd("user1", "secret") is True


def test_verify_htpasswd_sha1_wrong_password(tmp_path, monkeypatch):
    htpasswd = tmp_path / "htpasswd"
    _write_htpasswd(htpasswd, "user1", "secret", scheme="sha1")
    monkeypatch.setattr("app.core.config.settings.checkmk_htpasswd", str(htpasswd))
    monkeypatch.setattr("app.services.auth_service.settings.checkmk_htpasswd", str(htpasswd))
    assert _verify_htpasswd("user1", "wrongpassword") is False


def test_verify_htpasswd_bcrypt_correct(tmp_path, monkeypatch):
    htpasswd = tmp_path / "htpasswd"
    _write_htpasswd(htpasswd, "user2", "bcryptpw", scheme="bcrypt")
    monkeypatch.setattr("app.core.config.settings.checkmk_htpasswd", str(htpasswd))
    monkeypatch.setattr("app.services.auth_service.settings.checkmk_htpasswd", str(htpasswd))
    assert _verify_htpasswd("user2", "bcryptpw") is True


def test_verify_htpasswd_user_not_found(tmp_path, monkeypatch):
    htpasswd = tmp_path / "htpasswd"
    _write_htpasswd(htpasswd, "user1", "secret", scheme="sha1")
    monkeypatch.setattr("app.core.config.settings.checkmk_htpasswd", str(htpasswd))
    monkeypatch.setattr("app.services.auth_service.settings.checkmk_htpasswd", str(htpasswd))
    assert _verify_htpasswd("nonexistent", "secret") is False


def test_verify_htpasswd_no_path_configured(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.checkmk_htpasswd", "")
    monkeypatch.setattr("app.services.auth_service.settings.checkmk_htpasswd", "")
    assert _verify_htpasswd("user", "pw") is False


def test_verify_htpasswd_file_not_found(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.services.auth_service.settings.checkmk_htpasswd", str(tmp_path / "missing.htpasswd")
    )
    assert _verify_htpasswd("user", "pw") is False


def test_verify_htpasswd_skips_comment_lines(tmp_path, monkeypatch):
    htpasswd = tmp_path / "htpasswd"
    _write_htpasswd(htpasswd, "user1", "secret", scheme="sha1")
    # prepend a comment line
    htpasswd.write_text("# comment\n" + htpasswd.read_text(), encoding="utf-8")
    monkeypatch.setattr("app.services.auth_service.settings.checkmk_htpasswd", str(htpasswd))
    assert _verify_htpasswd("user1", "secret") is True


# ---------------------------------------------------------------------------
# validate_checkmk_cookie
# ---------------------------------------------------------------------------


def _make_cookie(
    tmp_path,
    username: str,
    session_id: str,
    serial: int = 0,
    *,
    session_state: str = "logged_in",
    two_factor_completed: bool = True,
    logged_out: bool = False,
    write_session_file: bool = True,
    two_factor_credentials: dict | None = None,
) -> str:
    secret = b"mysecret"
    (tmp_path / "etc").mkdir(exist_ok=True)
    (tmp_path / "etc" / "auth.secret").write_bytes(secret)
    user_dir = tmp_path / "var" / "check_mk" / "web" / username
    user_dir.mkdir(parents=True, exist_ok=True)
    (user_dir / "serial.mk").write_text(str(serial), encoding="utf-8")
    if write_session_file:
        # Mirror CMK's on-disk shape (repr of {session_id: asdict(SessionInfo)}).
        # 2.5+ uses session_state; 2.3/2.4 uses logged_out + two_factor_completed.
        session_info = {
            "session_id": session_id,
            "session_state": session_state,
            "logged_out": logged_out,
            "two_factor_completed": two_factor_completed,
        }
        (user_dir / "session_info.mk").write_text(
            repr({session_id: session_info}), encoding="utf-8"
        )
    if two_factor_credentials is not None:
        (user_dir / "two_factor_credentials.mk").write_text(
            repr(two_factor_credentials), encoding="utf-8"
        )
    msg = f"{username}{session_id}{serial}".encode()
    cookie_hash = _hmac.new(key=secret, msg=msg, digestmod=hashlib.sha256).digest().hex()
    return f"{username}:{session_id}:{cookie_hash}"


def test_validate_cookie_no_omd_root(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.checkmk_omd_root", "")
    monkeypatch.setattr("app.services.auth_service.settings.checkmk_omd_root", "")
    assert validate_checkmk_cookie("user:session:hash") is None


def test_validate_cookie_valid(tmp_path, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.checkmk_omd_root", str(tmp_path))
    monkeypatch.setattr("app.services.auth_service.settings.checkmk_omd_root", str(tmp_path))
    cookie = _make_cookie(tmp_path, "alice", "sess123", serial=5)
    assert validate_checkmk_cookie(cookie) == "alice"


def test_validate_cookie_wrong_hmac(tmp_path, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.checkmk_omd_root", str(tmp_path))
    monkeypatch.setattr("app.services.auth_service.settings.checkmk_omd_root", str(tmp_path))
    # Create valid structure but wrong hash
    (tmp_path / "etc").mkdir(exist_ok=True)
    (tmp_path / "etc" / "auth.secret").write_bytes(b"mysecret")
    assert validate_checkmk_cookie("alice:sess:wronghash") is None


def test_validate_cookie_unsafe_username(tmp_path, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.checkmk_omd_root", str(tmp_path))
    monkeypatch.setattr("app.services.auth_service.settings.checkmk_omd_root", str(tmp_path))
    (tmp_path / "etc").mkdir(exist_ok=True)
    (tmp_path / "etc" / "auth.secret").write_bytes(b"mysecret")
    # Path traversal attempt
    assert validate_checkmk_cookie("../etc/passwd:sess:hash") is None


def test_validate_cookie_no_auth_secret(tmp_path, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.checkmk_omd_root", str(tmp_path))
    monkeypatch.setattr("app.services.auth_service.settings.checkmk_omd_root", str(tmp_path))
    (tmp_path / "etc").mkdir(exist_ok=True)
    assert validate_checkmk_cookie("user:sess:hash") is None


def test_validate_cookie_wrong_format(tmp_path, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.checkmk_omd_root", str(tmp_path))
    monkeypatch.setattr("app.services.auth_service.settings.checkmk_omd_root", str(tmp_path))
    (tmp_path / "etc").mkdir(exist_ok=True)
    (tmp_path / "etc" / "auth.secret").write_bytes(b"secret")
    # Missing parts — only 2 colons
    assert validate_checkmk_cookie("user:onlyonepart") is None


def test_validate_cookie_rejects_pending_2fa_25(tmp_path, monkeypatch):
    """CMK 2.5+: session_state != 'logged_in' must block SSO even with valid HMAC."""
    monkeypatch.setattr("app.core.config.settings.checkmk_omd_root", str(tmp_path))
    monkeypatch.setattr("app.services.auth_service.settings.checkmk_omd_root", str(tmp_path))
    cookie = _make_cookie(
        tmp_path, "alice", "sess123", serial=5, session_state="second_factor_auth_needed"
    )
    assert validate_checkmk_cookie(cookie) is None


def test_validate_cookie_rejects_credentials_needed(tmp_path, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.checkmk_omd_root", str(tmp_path))
    monkeypatch.setattr("app.services.auth_service.settings.checkmk_omd_root", str(tmp_path))
    cookie = _make_cookie(
        tmp_path, "alice", "sess123", serial=5, session_state="credentials_needed"
    )
    assert validate_checkmk_cookie(cookie) is None


def test_validate_cookie_rejects_pending_2fa_24(tmp_path, monkeypatch):
    """CMK 2.3/2.4: 2FA-enabled user with two_factor_completed=False must be rejected.

    Simulates the older session_info.mk shape (no session_state field).
    """
    monkeypatch.setattr("app.core.config.settings.checkmk_omd_root", str(tmp_path))
    monkeypatch.setattr("app.services.auth_service.settings.checkmk_omd_root", str(tmp_path))
    secret = b"mysecret"
    (tmp_path / "etc").mkdir(exist_ok=True)
    (tmp_path / "etc" / "auth.secret").write_bytes(secret)
    user_dir = tmp_path / "var" / "check_mk" / "web" / "alice"
    user_dir.mkdir(parents=True, exist_ok=True)
    (user_dir / "serial.mk").write_text("0", encoding="utf-8")
    (user_dir / "session_info.mk").write_text(
        repr({"sess123": {"logged_out": False, "two_factor_completed": False}}),
        encoding="utf-8",
    )
    (user_dir / "two_factor_credentials.mk").write_text(
        repr(
            {
                "webauthn_credentials": {"cred1": {"id": "x"}},
                "totp_credentials": {},
                "backup_codes": [],
            }
        ),
        encoding="utf-8",
    )
    msg = b"alicesess1230"
    cookie_hash = _hmac.new(key=secret, msg=msg, digestmod=hashlib.sha256).digest().hex()
    assert validate_checkmk_cookie(f"alice:sess123:{cookie_hash}") is None


def test_validate_cookie_accepts_24_without_2fa_configured(tmp_path, monkeypatch):
    """CMK 2.3/2.4: user without any 2FA credentials passes the legacy gate."""
    monkeypatch.setattr("app.core.config.settings.checkmk_omd_root", str(tmp_path))
    monkeypatch.setattr("app.services.auth_service.settings.checkmk_omd_root", str(tmp_path))
    secret = b"mysecret"
    (tmp_path / "etc").mkdir(exist_ok=True)
    (tmp_path / "etc" / "auth.secret").write_bytes(secret)
    user_dir = tmp_path / "var" / "check_mk" / "web" / "alice"
    user_dir.mkdir(parents=True, exist_ok=True)
    (user_dir / "serial.mk").write_text("0", encoding="utf-8")
    (user_dir / "session_info.mk").write_text(
        repr({"sess123": {"logged_out": False, "two_factor_completed": False}}),
        encoding="utf-8",
    )
    msg = b"alicesess1230"
    cookie_hash = _hmac.new(key=secret, msg=msg, digestmod=hashlib.sha256).digest().hex()
    assert validate_checkmk_cookie(f"alice:sess123:{cookie_hash}") == "alice"


def test_validate_cookie_rejects_logged_out_24(tmp_path, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.checkmk_omd_root", str(tmp_path))
    monkeypatch.setattr("app.services.auth_service.settings.checkmk_omd_root", str(tmp_path))
    cookie = _make_cookie(
        tmp_path,
        "alice",
        "sess123",
        serial=5,
        session_state=None,  # type: ignore[arg-type]
        logged_out=True,
    )
    assert validate_checkmk_cookie(cookie) is None


def test_validate_cookie_rejects_unknown_session_id(tmp_path, monkeypatch):
    """Cookie HMAC valid but session_id not in session_info.mk (e.g. evicted)."""
    monkeypatch.setattr("app.core.config.settings.checkmk_omd_root", str(tmp_path))
    monkeypatch.setattr("app.services.auth_service.settings.checkmk_omd_root", str(tmp_path))
    cookie = _make_cookie(tmp_path, "alice", "sess123", serial=5)
    user_dir = tmp_path / "var" / "check_mk" / "web" / "alice"
    # Overwrite session file with a different session id
    (user_dir / "session_info.mk").write_text(
        repr({"OTHER_SESSION": {"session_state": "logged_in"}}), encoding="utf-8"
    )
    assert validate_checkmk_cookie(cookie) is None


def test_validate_cookie_rejects_missing_session_file(tmp_path, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.checkmk_omd_root", str(tmp_path))
    monkeypatch.setattr("app.services.auth_service.settings.checkmk_omd_root", str(tmp_path))
    cookie = _make_cookie(tmp_path, "alice", "sess123", serial=5, write_session_file=False)
    assert validate_checkmk_cookie(cookie) is None


# ---------------------------------------------------------------------------
# user_has_two_factor_enabled
# ---------------------------------------------------------------------------


def _write_two_factor_credentials(tmp_path, username: str, creds: dict) -> None:
    user_dir = tmp_path / "var" / "check_mk" / "web" / username
    user_dir.mkdir(parents=True, exist_ok=True)
    (user_dir / "two_factor_credentials.mk").write_text(repr(creds), encoding="utf-8")


def test_two_factor_enabled_no_omd_root(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.checkmk_omd_root", "")
    monkeypatch.setattr("app.services.auth_service.settings.checkmk_omd_root", "")
    assert user_has_two_factor_enabled("alice") is False


def test_two_factor_enabled_with_totp(tmp_path, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.checkmk_omd_root", str(tmp_path))
    monkeypatch.setattr("app.services.auth_service.settings.checkmk_omd_root", str(tmp_path))
    _write_two_factor_credentials(
        tmp_path,
        "alice",
        {"webauthn_credentials": {}, "totp_credentials": {"t1": {"secret": "x"}}},
    )
    assert user_has_two_factor_enabled("alice") is True


def test_two_factor_enabled_with_webauthn(tmp_path, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.checkmk_omd_root", str(tmp_path))
    monkeypatch.setattr("app.services.auth_service.settings.checkmk_omd_root", str(tmp_path))
    _write_two_factor_credentials(
        tmp_path,
        "alice",
        {"webauthn_credentials": {"c1": {"id": "x"}}, "totp_credentials": {}},
    )
    assert user_has_two_factor_enabled("alice") is True


def test_two_factor_disabled_when_no_credentials(tmp_path, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.checkmk_omd_root", str(tmp_path))
    monkeypatch.setattr("app.services.auth_service.settings.checkmk_omd_root", str(tmp_path))
    assert user_has_two_factor_enabled("alice") is False


def test_two_factor_disabled_when_empty_credentials(tmp_path, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.checkmk_omd_root", str(tmp_path))
    monkeypatch.setattr("app.services.auth_service.settings.checkmk_omd_root", str(tmp_path))
    _write_two_factor_credentials(
        tmp_path,
        "alice",
        {"webauthn_credentials": {}, "totp_credentials": {}, "backup_codes": []},
    )
    assert user_has_two_factor_enabled("alice") is False


def test_two_factor_rejects_unsafe_username(tmp_path, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.checkmk_omd_root", str(tmp_path))
    monkeypatch.setattr("app.services.auth_service.settings.checkmk_omd_root", str(tmp_path))
    assert user_has_two_factor_enabled("../etc/passwd") is False


# ---------------------------------------------------------------------------
# get_cmk_language
# ---------------------------------------------------------------------------


def test_get_cmk_language_no_omd_root(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.checkmk_omd_root", "")
    monkeypatch.setattr("app.services.auth_service.settings.checkmk_omd_root", "")
    assert get_cmk_language("user") is None


def test_get_cmk_language_de(tmp_path, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.checkmk_omd_root", str(tmp_path))
    monkeypatch.setattr("app.services.auth_service.settings.checkmk_omd_root", str(tmp_path))
    monkeypatch.setattr("app.services.auth_service.cmk_integration.available", False)
    lang_dir = tmp_path / "var" / "check_mk" / "web" / "alice"
    lang_dir.mkdir(parents=True)
    (lang_dir / "language.mk").write_text("de", encoding="utf-8")
    assert get_cmk_language("alice") == "de"


def test_get_cmk_language_unsupported_maps_to_en(tmp_path, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.checkmk_omd_root", str(tmp_path))
    monkeypatch.setattr("app.services.auth_service.settings.checkmk_omd_root", str(tmp_path))
    monkeypatch.setattr("app.services.auth_service.cmk_integration.available", False)
    lang_dir = tmp_path / "var" / "check_mk" / "web" / "alice"
    lang_dir.mkdir(parents=True)
    (lang_dir / "language.mk").write_text("fr", encoding="utf-8")
    assert get_cmk_language("alice") == "en"


def test_get_cmk_language_no_file_returns_none(tmp_path, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.checkmk_omd_root", str(tmp_path))
    monkeypatch.setattr("app.services.auth_service.settings.checkmk_omd_root", str(tmp_path))
    monkeypatch.setattr("app.services.auth_service.cmk_integration.available", False)
    assert get_cmk_language("bob") is None


# ---------------------------------------------------------------------------
# authenticate_user
# ---------------------------------------------------------------------------


def _insert_test_user(conn, name: str, password: str, is_active: bool = True) -> None:
    from app.core.security import hash_password

    conn.execute(
        "INSERT INTO users (name, password, is_active, is_admin, must_change_password) "
        "VALUES (?, ?, ?, 0, 0)",
        (name, hash_password(password), 1 if is_active else 0),
    )


@pytest.mark.asyncio
async def test_authenticate_user_correct_credentials(db_session):
    _insert_test_user(db_session, "testauth", "correct")
    result = await authenticate_user(db_session, "testauth", "correct")
    assert result is not None
    assert result.name == "testauth"


@pytest.mark.asyncio
async def test_authenticate_user_wrong_password(db_session):
    _insert_test_user(db_session, "authuser2", "correct")
    result = await authenticate_user(db_session, "authuser2", "wrongpw")
    assert result is None


@pytest.mark.asyncio
async def test_authenticate_user_inactive_returns_none(db_session):
    _insert_test_user(db_session, "inactive", "pw", is_active=False)
    result = await authenticate_user(db_session, "inactive", "pw")
    assert result is None


@pytest.mark.asyncio
async def test_authenticate_user_unknown_username_no_error(db_session, monkeypatch):
    monkeypatch.setattr("app.services.auth_service.settings.checkmk_htpasswd", "")
    # Should not raise, just return None
    result = await authenticate_user(db_session, "doesnotexist", "pw")
    assert result is None


# ---------------------------------------------------------------------------
# get_or_create_sso_user
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_or_create_sso_user_creates_new(db_session, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.checkmk_omd_root", "")
    monkeypatch.setattr("app.services.auth_service.settings.checkmk_omd_root", "")
    user = await get_or_create_sso_user(db_session, "ssouser1")
    assert user.name == "ssouser1"
    assert user.is_active is True


@pytest.mark.asyncio
async def test_get_or_create_sso_user_returns_existing(db_session, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.checkmk_omd_root", "")
    monkeypatch.setattr("app.services.auth_service.settings.checkmk_omd_root", "")

    user1 = await get_or_create_sso_user(db_session, "ssouser2")
    user2 = await get_or_create_sso_user(db_session, "ssouser2")
    assert user1.user_id == user2.user_id
