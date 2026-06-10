"""Authentication schemas."""

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=150)
    password: str = Field(..., min_length=1, max_length=1000)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class StreamTicketResponse(BaseModel):
    """Short-lived token for URL-borne auth (SSE / tile <img> fetches)."""

    ticket: str
    expires_in: int
