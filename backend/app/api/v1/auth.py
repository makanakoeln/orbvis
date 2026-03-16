"""Authentication endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.core.security import create_access_token, create_refresh_token, decode_token
from app.models.user import User
from app.schemas.auth import LoginRequest, RefreshRequest, TokenResponse
from app.schemas.user import UserRead
from app.services.auth_service import (
    authenticate_user,
    create_tokens,
    get_cmk_language,
    get_cmk_theme,
    get_or_create_sso_user,
    get_user_by_id,
    validate_checkmk_cookie,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    user = await authenticate_user(db, data.username, data.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    return create_tokens(user)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    data: RefreshRequest, db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid refresh token",
    )
    try:
        payload = decode_token(data.refresh_token)
        if payload.get("type") != "refresh":
            raise credentials_exception
        user_id = int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        raise credentials_exception

    user = await get_user_by_id(db, user_id)
    if user is None or not user.is_active:
        raise credentials_exception

    return TokenResponse(
        access_token=create_access_token(user.user_id),
        refresh_token=create_refresh_token(user.user_id),
    )


@router.get("/me", response_model=UserRead)
async def me(current_user: User = Depends(get_current_user)) -> UserRead:
    result = UserRead.model_validate(current_user)
    result.cmk_theme = get_cmk_theme(current_user.name)
    result.cmk_language = get_cmk_language(current_user.name)
    return result


@router.get("/sso", response_model=TokenResponse)
async def sso_login(request: Request, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    """SSO via Checkmk session cookie (auth_<site>).

    The browser automatically sends the Checkmk cookie with every same-origin request.
    The backend validates the cookie HMAC against the OMD auth.secret file.
    """
    site = settings.checkmk_site
    cookie_name = f"auth_{site}" if site else None
    username: str | None = None

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
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No valid Checkmk session")
    logger.info("SSO: login successful for user %r", username)

    user = await get_or_create_sso_user(db, username)
    return create_tokens(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(_: User = Depends(get_current_user)) -> None:
    # JWT is stateless; client discards the token.
    # For server-side invalidation, add a token blocklist here.
    return None
