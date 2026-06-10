"""Tests for the security validators added before public release."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.api.v1.connections import (
    HostActionRequest,
    ServiceActionRequest,
    _build_host_command,
    _build_service_command,
)
from app.core.image_security import is_safe_svg, is_valid_image
from app.models.user import User
from app.schemas.board import BoardObject, BoardObjectUpdate, normalize_object_filter
from app.schemas.connection import REDACTED_SECRET, ConnectionConfig, _redact


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
        ConnectionConfig(id="b1", type="test", checkmk_url=url)

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
            ConnectionConfig(id="b1", checkmk_url=url)

    def test_rejects_traversal_in_relative_path(self) -> None:
        with pytest.raises(ValidationError):
            ConnectionConfig(id="b1", checkmk_url="/CMC/../../etc/passwd")

    def test_rejects_overlong_url(self) -> None:
        with pytest.raises(ValidationError):
            ConnectionConfig(id="b1", checkmk_url="http://example.com/" + "a" * 3000)


class TestBackendSecretRedaction:
    def test_redact_replaces_secrets(self) -> None:
        cfg = ConnectionConfig(
            id="b1",
            type="test",
            automation_secret="real-secret",
            icinga2_password="real-pw",
        )
        redacted = _redact(cfg)
        assert redacted.automation_secret == REDACTED_SECRET
        assert redacted.icinga2_password == REDACTED_SECRET

    def test_redact_keeps_none(self) -> None:
        cfg = ConnectionConfig(id="b1", type="test")
        redacted = _redact(cfg)
        assert redacted.automation_secret is None
        assert redacted.icinga2_password is None


class TestBoardObjectUrlValidation:
    """Block javascript:/data:/etc. on user-supplied object URLs (XSS guard)."""

    @pytest.mark.parametrize("field", ["url", "hover_url", "graph_url"])
    @pytest.mark.parametrize(
        "scheme",
        [
            "javascript:",
            "data:",
            "vbscript:",
            "file:",
            "JavaScript:",
            " javascript:",
            # Browsers strip ASCII control chars when parsing URLs, so these
            # would still execute on click — the validator must reject them.
            "java\tscript:",
            "java\nscript:",
            "java\rscript:",
            "\x01javascript:",
            # Allowlist posture: unknown schemes are rejected outright.
            "blob:",
            "chrome:",
            "about:",
        ],
    )
    def test_rejects_xss_schemes(self, field: str, scheme: str) -> None:
        with pytest.raises(ValidationError):
            BoardObject(id="o1", type="image", **{field: scheme + "alert(1)"})
        with pytest.raises(ValidationError):
            BoardObjectUpdate(**{field: scheme + "alert(1)"})

    @pytest.mark.parametrize("field", ["url", "hover_url", "graph_url"])
    @pytest.mark.parametrize(
        "url",
        [
            "https://example.com/x",
            "http://example.com/x",
            "mailto:ops@example.com",
            "tel:+491234567",
            # Remote-access handlers monitoring boards traditionally link.
            "ssh://switch01",
            "rdp://winserver",
            "vnc://kvm01",
            "/relative/path?x=1",
            "view.py?view_name=host",
            "//cdn.example.com/x",
        ],
    )
    def test_accepts_safe_urls(self, field: str, url: str) -> None:
        BoardObject(id="o1", type="image", **{field: url})


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

    def test_accepts_doctype_export(self) -> None:
        # Illustrator/Inkscape exports carry the standard SVG DOCTYPE; it must
        # be accepted (entity/external protections stay on, see below).
        good = (
            b'<?xml version="1.0" encoding="utf-8"?>\n'
            b'<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" '
            b'"http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">\n'
            b'<svg xmlns="http://www.w3.org/2000/svg"><rect/></svg>'
        )
        assert is_safe_svg(good) is True

    def test_rejects_billion_laughs(self) -> None:
        bad = (
            b'<?xml version="1.0"?><!DOCTYPE lolz ['
            b'<!ENTITY lol "lol"><!ENTITY lol2 "&lol;&lol;">]>'
            b'<svg xmlns="http://www.w3.org/2000/svg">&lol2;</svg>'
        )
        assert is_safe_svg(bad) is False

    def test_rejects_xxe_external_entity(self) -> None:
        bad = (
            b'<?xml version="1.0"?><!DOCTYPE svg ['
            b'<!ENTITY xxe SYSTEM "file:///etc/passwd">]>'
            b'<svg xmlns="http://www.w3.org/2000/svg">&xxe;</svg>'
        )
        assert is_safe_svg(bad) is False

    def test_accepts_internal_use_reference(self) -> None:
        good = (
            b'<svg xmlns="http://www.w3.org/2000/svg" '
            b'xmlns:xlink="http://www.w3.org/1999/xlink">'
            b'<defs><rect id="r"/></defs><use xlink:href="#r"/></svg>'
        )
        assert is_safe_svg(good) is True

    def test_rejects_remote_use_reference(self) -> None:
        bad = (
            b'<svg xmlns="http://www.w3.org/2000/svg" '
            b'xmlns:xlink="http://www.w3.org/1999/xlink">'
            b'<use xlink:href="https://evil.example/x.svg#a"/></svg>'
        )
        assert is_safe_svg(bad) is False

    def test_accepts_embedded_raster_data_uri(self) -> None:
        good = (
            b'<svg xmlns="http://www.w3.org/2000/svg" '
            b'xmlns:xlink="http://www.w3.org/1999/xlink">'
            b'<image xlink:href="data:image/png;base64,iVBORw0KGgo="/></svg>'
        )
        assert is_safe_svg(good) is True

    def test_rejects_svg_data_uri(self) -> None:
        bad = (
            b'<svg xmlns="http://www.w3.org/2000/svg" '
            b'xmlns:xlink="http://www.w3.org/1999/xlink">'
            b'<image xlink:href="data:image/svg+xml;base64,PHN2Zz48L3N2Zz4="/></svg>'
        )
        assert is_safe_svg(bad) is False

    def test_valid_image_accepts_svg_after_long_preamble(self) -> None:
        # A long licence comment must not push <svg> out of the sniff window.
        good = (
            b'<?xml version="1.0"?>\n<!-- ' + b"x" * 600 + b" -->\n"
            b'<svg xmlns="http://www.w3.org/2000/svg"><rect/></svg>'
        )
        assert is_valid_image(good) is True


class TestDyngroupFilterValidation:
    """object_filter is forwarded to Livestatus, so non-Filter headers must not
    survive — including ones smuggled in via an escaped ``\\n``."""

    def test_single_line_without_trailing_newline_is_accepted(self) -> None:
        # NagVis stores single-filter dyngroups without a trailing separator.
        assert normalize_object_filter("Filter: host_name ~ ^web") == "Filter: host_name ~ ^web\n"

    def test_normalises_literal_backslash_n_separator(self) -> None:
        out = normalize_object_filter("Filter: a\\nFilter: b")
        assert out == "Filter: a\nFilter: b\n"

    def test_accepts_combinator_headers(self) -> None:
        out = normalize_object_filter("Filter: a\\nFilter: b\\nOr: 2")
        assert out == "Filter: a\nFilter: b\nOr: 2\n"

    @pytest.mark.parametrize(
        "value",
        [
            "Filter: a\\nStats: state = 0",
            "Filter: a\\nColumns: name address",
            "Filter: a\\nOutputFormat: python",
            "Filter: a\\nGET hosts",
            "Filter: a\\nAuthUser: admin",
            "Stats: state = 0",
            "GET hosts",
        ],
    )
    def test_rejects_injected_headers(self, value: str) -> None:
        with pytest.raises(ValueError):
            normalize_object_filter(value)

    def test_board_object_rejects_injection(self) -> None:
        with pytest.raises(ValidationError):
            BoardObject(
                id="d1",
                type="dyngroup",
                object_filter="Filter: a\\nStats: state = 0",
            )

    def test_board_object_update_normalises_filter(self) -> None:
        obj = BoardObjectUpdate(object_filter="Filter: host_name ~ ^web")
        assert obj.object_filter == "Filter: host_name ~ ^web\n"


class TestCommandInjection:
    """Host/service names reach the livestatus command pipe via
    ``COMMAND [ts] <body>\\n``. A crafted name must not be able to inject a
    second COMMAND line (newline) or forge command fields (``;``)."""

    _ADMIN = User(user_id=1, name="admin", is_admin=True)

    @pytest.mark.parametrize(
        "name",
        [
            "host\nCOMMAND [0] DISABLE_NOTIFICATIONS;evil",
            "host;sneaky",
            "host\rmalice",
        ],
    )
    def test_host_schema_rejects_separators(self, name: str) -> None:
        with pytest.raises(ValidationError):
            HostActionRequest(action="force_check", host_name=name)

    @pytest.mark.parametrize("field", ["host_name", "service_description"])
    def test_service_schema_rejects_separators(self, field: str) -> None:
        kwargs = {"action": "force_check", "host_name": "h", "service_description": "s"}
        kwargs[field] = "x\nGET hosts"
        with pytest.raises(ValidationError):
            ServiceActionRequest(**kwargs)

    def test_builder_sanitizes_simple_host_command(self) -> None:
        # Defense-in-depth: even if a name bypasses the schema validator, the
        # builder must neutralise separators before they reach the pipe.
        body = HostActionRequest.model_construct(action="force_check", host_name="host\nINJECT;x")
        cmd = _build_host_command(body, self._ADMIN)
        assert "\n" not in cmd and "\r" not in cmd
        assert cmd.startswith("SCHEDULE_FORCED_HOST_CHECK;host INJECT x;")

    def test_builder_sanitizes_simple_service_command(self) -> None:
        body = ServiceActionRequest.model_construct(
            action="force_check", host_name="h\nx", service_description="s;y"
        )
        cmd = _build_service_command(body, self._ADMIN)
        assert "\n" not in cmd and "\r" not in cmd
        assert cmd.startswith("SCHEDULE_FORCED_SVC_CHECK;h x;s y;")
