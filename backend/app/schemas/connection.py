"""Pydantic schemas for monitoring connection configuration."""

from __future__ import annotations

from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator

# Hosts that should never be reached via the credentialed outbound HTTP path:
# cloud-provider metadata services that would happily hand back IAM tokens to
# anyone who knows to ask. See OWASP SSRF cheatsheet.
_BLOCKED_HOSTS = frozenset(
    {
        "169.254.169.254",  # AWS / GCP / Azure IMDS v1/v2
        "metadata.google.internal",
        "metadata",
    }
)


def _validate_socket_path(value: str | None) -> str | None:
    """Reject Unix-socket paths that an admin shouldn't be able to set.

    Defense in depth: the FormSpec / API endpoints are already admin-gated, but
    the path is fed to the Livestatus client without any further check. Without
    these rules a careless admin could probe arbitrary files (``/etc/shadow``)
    via the connection-test endpoint, or break the connection-storage layer
    with a path containing NULs.
    """
    if value is None or value == "":
        return value
    if "\x00" in value:
        raise ValueError("Socket path must not contain NUL byte")
    if not value.startswith("/"):
        raise ValueError("Socket path must be absolute")
    if ".." in value.split("/"):
        raise ValueError("Socket path must not contain '..'")
    return value


def _validate_safe_url(value: str | None) -> str | None:
    """Restrict checkmk_url / icinga2_url to safe forms.

    Accepts:
      - empty / None
      - absolute path (``/<site>/check_mk``) — OrbVis prepends ``http://127.0.0.1``
      - http(s) URL to a non-metadata host
    Rejects ``javascript:``, ``file:``, ``data:``, userinfo (``user:pass@``),
    and known cloud-metadata hosts.
    """
    if not value:
        return value
    if len(value) > 2048:
        raise ValueError("URL too long")
    s = value.strip()
    if s.startswith("/"):
        if ".." in s.split("/"):
            raise ValueError("URL must not contain '..'")
        return s
    parsed = urlparse(s)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Unsupported URL scheme: {parsed.scheme!r}")
    if parsed.username or parsed.password:
        raise ValueError("URL must not contain userinfo")
    host = (parsed.hostname or "").lower()
    if host in _BLOCKED_HOSTS:
        raise ValueError(f"Host {host!r} is blocked")
    return s


# Sentinel returned in API responses in place of real secrets. Frontend echoes
# this back unchanged on edit; the route preserves the existing secret in that
# case (see app.api.v1.connections.update_backend).
REDACTED_SECRET = "***REDACTED***"


class ConnectionConfig(BaseModel):
    id: str = Field(..., max_length=64, pattern=r"^[a-zA-Z0-9_\-]+$")
    type: Literal["livestatus", "icinga2", "test"] = "livestatus"
    label: str = Field(default="", max_length=200)
    # Livestatus connection (Unix socket OR TCP, not both)
    socket_path: str | None = Field(default=None, max_length=512)
    host: str | None = Field(default=None, max_length=255)
    # Optional: unix-socket-only setups have no port; UI also emits null when cleared.
    port: int | None = Field(default=None, ge=1, le=65535)
    # TLS for the TCP livestatus path (OMD's `LIVESTATUS_TLS=on` ships stunnel
    # on the 6557 listener). Ignored for unix-socket connections. Defaults to
    # on because every supported OMD version enables TLS by default in current
    # site setups, and a plain TCP connect against a TLS port looks "open" but
    # silently returns garbage — see livestatus.py _query_raw.
    tls: bool = True
    # Default off: OMD ships a self-signed per-site CA which would otherwise
    # need an explicit CA bundle to verify. Admins running with a properly
    # signed cert can opt in.
    tls_verify: bool = False
    timeout: float = Field(default=10.0, ge=0.1, le=300.0)
    checkmk_url: str | None = Field(default=None, description="e.g. /<site>/check_mk")
    automation_user: str | None = Field(default=None, max_length=200)
    automation_secret: str | None = Field(default=None, max_length=512)
    # Icinga2 REST API connection
    icinga2_url: str | None = Field(default=None, description="e.g. https://<host>:5665")
    icinga2_username: str | None = Field(default=None, max_length=200)
    icinga2_password: str | None = Field(default=None, max_length=512)
    icinga2_verify_ssl: bool = True

    @field_validator("checkmk_url", "icinga2_url")
    @classmethod
    def _safe_url(cls, v: str | None) -> str | None:
        return _validate_safe_url(v)

    @field_validator("socket_path")
    @classmethod
    def _safe_socket_path(cls, v: str | None) -> str | None:
        return _validate_socket_path(v)


def _redact(cfg: ConnectionConfig) -> ConnectionConfig:
    """Return a copy of *cfg* with secrets replaced by ``REDACTED_SECRET``.

    Used for API responses so credentials never leave the server. The
    redaction sentinel is recognised by ``update_backend`` to mean
    "keep the stored value".
    """
    return cfg.model_copy(
        update={
            "automation_secret": REDACTED_SECRET if cfg.automation_secret else None,
            "icinga2_password": REDACTED_SECRET if cfg.icinga2_password else None,
        }
    )


ConnectionCreate = ConnectionConfig


class ConnectionUpdate(BaseModel):
    """Full replacement of all mutable fields (id stays fixed)."""

    type: Literal["livestatus", "icinga2", "test"] = "livestatus"
    label: str = Field(default="", max_length=200)
    socket_path: str | None = Field(default=None, max_length=512)
    host: str | None = Field(default=None, max_length=255)
    port: int | None = Field(default=None, ge=1, le=65535)
    tls: bool = True
    tls_verify: bool = False
    timeout: float = Field(default=10.0, ge=0.1, le=300.0)
    checkmk_url: str | None = None
    automation_user: str | None = Field(default=None, max_length=200)
    automation_secret: str | None = Field(default=None, max_length=512)
    icinga2_url: str | None = None
    icinga2_username: str | None = Field(default=None, max_length=200)
    icinga2_password: str | None = Field(default=None, max_length=512)
    icinga2_verify_ssl: bool = True

    @field_validator("checkmk_url", "icinga2_url")
    @classmethod
    def _safe_url(cls, v: str | None) -> str | None:
        return _validate_safe_url(v)

    @field_validator("socket_path")
    @classmethod
    def _safe_socket_path(cls, v: str | None) -> str | None:
        return _validate_socket_path(v)
