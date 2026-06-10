"""Authentication endpoints."""

from __future__ import annotations

import logging
import sqlite3
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials

from app.api.v1.deps import (
    allowed_command_actions,
    bearer,
    can_configure,
    can_create_board,
    get_current_user,
)
from app.core import _jwt
from app.core.config import settings
from app.core.database import get_db
from app.core.ratelimit import login_limiter
from app.core.security import (
    STREAM_TICKET_TTL,
    blocklist_token,
    create_access_token,
    create_refresh_token,
    create_stream_ticket,
    decode_token,
    is_token_blocked,
)
from app.models.user import User
from app.schemas.auth import LoginRequest, RefreshRequest, StreamTicketResponse, TokenResponse
from app.schemas.user import UserRead
from app.services.auth_service import (
    authenticate_user,
    checkmk_cookie_needs_two_factor,
    create_tokens,
    get_cmk_language,
    get_cmk_theme,
    get_or_create_sso_user,
    get_user_by_id,
    user_has_two_factor_enabled,
    validate_checkmk_cookie,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
async def login(
    data: LoginRequest, request: Request, db: sqlite3.Connection = Depends(get_db)
) -> TokenResponse:
    client_ip = request.client.host if request.client else "unknown"
    if login_limiter.is_blocked(client_ip):
        retry = login_limiter.retry_after(client_ip)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many login attempts. Try again in {int(retry) + 1}s.",
            headers={"Retry-After": str(int(retry) + 1)},
        )
    user = await authenticate_user(db, data.username, data.password)
    if user is None:
        login_limiter.record(client_ip)
        logger.info("login: failed for user %r from %s", data.username, client_ip)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    if user_has_two_factor_enabled(user.name):
        logger.warning(
            "login: refusing password-only login for %r — 2FA is enabled, SSO required",
            user.name,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Two-factor authentication is enabled for this account. "
            "Please sign in through Checkmk.",
        )
    logger.debug("login: success for user %r", user.name)
    return create_tokens(user)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    data: RefreshRequest, db: sqlite3.Connection = Depends(get_db)
) -> TokenResponse:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid refresh token",
    )
    try:
        payload = decode_token(data.refresh_token)
        if payload.get("type") != "refresh":
            raise credentials_exception
        user_id = int(str(payload["sub"]))
        jti = str(payload.get("jti", ""))
        exp = payload.get("exp")
    except (_jwt.PyJWTError, KeyError, ValueError):
        raise credentials_exception from None

    # Reject reuse of a refresh token that was already rotated or logged out.
    if jti and is_token_blocked(jti):
        raise credentials_exception

    user = await get_user_by_id(db, user_id)
    if user is None or not user.is_active:
        raise credentials_exception

    if jti:
        expiry = (
            datetime.fromtimestamp(float(str(exp)), tz=UTC)
            if exp
            else datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days)
        )
        blocklist_token(jti, expiry)

    logger.debug("refresh: rotated tokens for user %r (jti=%s)", user.name, jti)
    return TokenResponse(
        access_token=create_access_token(user.user_id),
        refresh_token=create_refresh_token(user.user_id),
    )


@router.get("/me", response_model=UserRead)
async def me(current_user: User = Depends(get_current_user)) -> UserRead:
    result = UserRead.model_validate(current_user)
    result.cmk_theme = get_cmk_theme(current_user.name)
    result.cmk_language = get_cmk_language(current_user.name)
    result.can_configure = can_configure(current_user)
    result.can_create_boards = can_create_board(current_user)
    result.command_permissions = allowed_command_actions(current_user)
    from app.integrations.checkmk import load_user_inline_help

    result.cmk_inline_help = load_user_inline_help(current_user.name)
    return result


@router.get("/sso", response_model=TokenResponse)
async def sso_login(request: Request, db: sqlite3.Connection = Depends(get_db)) -> TokenResponse:
    """SSO via Checkmk session cookie (auth_<site>).

    The browser sends the Checkmk cookie with every same-origin request; the
    backend validates the cookie HMAC against the OMD auth.secret file.
    """
    site = settings.checkmk_site
    cookie_name = f"auth_{site}" if site else None
    username: str | None = None
    cookie_value: str | None = None

    if not cookie_name:
        logger.warning("SSO: CHECKMK_SITE not configured (checkmk_site=%r)", settings.checkmk_site)
    else:
        cookie_value = request.cookies.get(cookie_name)
        if not cookie_value:
            logger.warning(
                "SSO: cookie %r not present — available cookies: %s",
                cookie_name,
                list(request.cookies.keys()),
            )
        else:
            username = validate_checkmk_cookie(cookie_value)

    if not username:
        # Distinguish "logged into Checkmk but 2FA pending" from "no session":
        # only the former lets the frontend bounce to user_login_two_factor.py.
        # "two_factor_required" is an internal sentinel, never shown to the user.
        if cookie_value and checkmk_cookie_needs_two_factor(cookie_value):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="two_factor_required"
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="No valid Checkmk session"
        )
    logger.debug("SSO: login successful for user %r", username)

    user = await get_or_create_sso_user(db, username)
    return create_tokens(user)


@router.post("/stream-ticket", response_model=StreamTicketResponse)
async def issue_stream_ticket(
    current_user: User = Depends(get_current_user),
) -> StreamTicketResponse:
    """Issue a short-lived ticket for URL-borne auth (SSE / tile fetches).

    EventSource and <img> cannot set an Authorization header, so those
    consumers carry their credential in the query string — which proxies log.
    The ticket bounds that exposure to minutes.
    """
    return StreamTicketResponse(
        ticket=create_stream_ticket(current_user.user_id),
        expires_in=int(STREAM_TICKET_TTL.total_seconds()),
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    _: User = Depends(get_current_user),
) -> None:
    try:
        payload = decode_token(credentials.credentials)
        jti = payload.get("jti", "")
        exp = payload.get("exp")
        expiry = datetime.fromtimestamp(float(str(exp)), tz=UTC) if exp else datetime.now(UTC)
        if jti:
            blocklist_token(str(jti), expiry)
    except Exception as exc:
        logger.warning("logout: failed to blocklist token: %s", exc)
