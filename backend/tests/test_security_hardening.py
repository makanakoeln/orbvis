"""Tests for the security validators added before public release."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.image_security import is_safe_svg
from app.schemas.backend import REDACTED_SECRET, BackendConfig, _redact
from app.schemas.board import BoardObject, BoardObjectUpdate


class TestBackendUrlValidation:
    """SSRF mitigations on checkmk_url / icinga2_url."""

    @pytest.mark.parametrize(
        "url",
        [
            "/CMC/check_mk",
            "http://localhost/heute",
            "https://monitor.example.com/check_mk",
            None,
            "",
        ],
    )
    def test_accepts_safe_urls(self, url: str | None) -> None:
        BackendConfig(id="b1", checkmk_url=url)

    @pytest.mark.parametrize(
        "url",
        [
            "javascript:alert(1)",
            "file:///etc/passwd",
            "data:text/html,<script>",
            "ftp://example.com",
            "http://user:pass@example.com",
            "http://169.254.169.254/latest/meta-data",
        ],
    )
    def test_rejects_dangerous_urls(self, url: str) -> None:
        with pytest.raises(ValidationError):
            BackendConfig(id="b1", checkmk_url=url)

    def test_rejects_traversal_in_relative_path(self) -> None:
        with pytest.raises(ValidationError):
            BackendConfig(id="b1", checkmk_url="/CMC/../../etc/passwd")

    def test_rejects_overlong_url(self) -> None:
        with pytest.raises(ValidationError):
            BackendConfig(id="b1", checkmk_url="http://example.com/" + "a" * 3000)


class TestBackendSecretRedaction:
    def test_redact_replaces_secrets(self) -> None:
        cfg = BackendConfig(
            id="b1",
            automation_secret="real-secret",
            icinga2_password="real-pw",
        )
        redacted = _redact(cfg)
        assert redacted.automation_secret == REDACTED_SECRET
        assert redacted.icinga2_password == REDACTED_SECRET

    def test_redact_keeps_none(self) -> None:
        cfg = BackendConfig(id="b1")
        redacted = _redact(cfg)
        assert redacted.automation_secret is None
        assert redacted.icinga2_password is None


class TestBoardObjectUrlValidation:
    """Block javascript:/data:/etc. on user-supplied object URLs (XSS guard)."""

    @pytest.mark.parametrize("field", ["url", "hover_url", "graph_url"])
    @pytest.mark.parametrize(
        "scheme",
        ["javascript:", "data:", "vbscript:", "file:", "JavaScript:", " javascript:"],
    )
    def test_rejects_xss_schemes(self, field: str, scheme: str) -> None:
        with pytest.raises(ValidationError):
            BoardObject(id="o1", type="image", **{field: scheme + "alert(1)"})
        with pytest.raises(ValidationError):
            BoardObjectUpdate(**{field: scheme + "alert(1)"})

    @pytest.mark.parametrize("field", ["url", "hover_url", "graph_url"])
    def test_accepts_http(self, field: str) -> None:
        BoardObject(id="o1", type="image", **{field: "https://example.com/x"})


class TestSvgSafety:
    def test_strips_script_tag(self) -> None:
        bad = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'
        assert is_safe_svg(bad) is False

    def test_strips_onload_attribute(self) -> None:
        bad = b'<svg xmlns="http://www.w3.org/2000/svg" onload="alert(1)"></svg>'
        assert is_safe_svg(bad) is False

    def test_strips_javascript_href(self) -> None:
        bad = (
            b'<svg xmlns="http://www.w3.org/2000/svg">'
            b'<a href="javascript:alert(1)"><circle r="5"/></a></svg>'
        )
        assert is_safe_svg(bad) is False

    def test_accepts_plain_svg(self) -> None:
        good = b'<svg xmlns="http://www.w3.org/2000/svg"><circle r="5" cx="5" cy="5"/></svg>'
        assert is_safe_svg(good) is True

    def test_rejects_foreign_object(self) -> None:
        bad = (
            b'<svg xmlns="http://www.w3.org/2000/svg">'
            b'<foreignObject><body xmlns="http://www.w3.org/1999/xhtml">x</body></foreignObject>'
            b"</svg>"
        )
        assert is_safe_svg(bad) is False
