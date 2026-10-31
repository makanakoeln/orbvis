"""Tests for the security validators added before public release."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.api.v1.connections import (
    HostActionRequest,
    ServiceActionRequest,
    _build_action_command,
)
from app.connections.base import MetricHistoryResult
from app.connections.livestatus import LivestatusConnection
from app.core.image_security import is_safe_svg, is_valid_image
from app.models.user import User
from app.schemas.board import (
    BoardConfig,
    BoardCreate,
    BoardObject,
    BoardObjectUpdate,
    BoardUpdate,
    DisplayConfig,
    RadarView,
    normalize_object_filter,
)
from app.schemas.connection import REDACTED_SECRET, ConnectionConfig, _redact
from app.services.board_service import _sanitize_legacy_data


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


_UNSAFE_ASSET_REFS = [
    "../../check_mk/logout.py",
    "sub/icon.png",
    "..\\icon.png",
    "https://evil.example/x.png",
    "javascript:alert(1)",
    "icon\n.png",
]


class TestAssetRefValidation:
    """Icon/background references stay bare filenames inside their asset directory."""

    @pytest.mark.parametrize("ref", _UNSAFE_ASSET_REFS)
    def test_rejects_unsafe_refs_on_save(self, ref: str) -> None:
        with pytest.raises(ValidationError):
            BoardObject(id="o1", type="image", image_src=ref)
        with pytest.raises(ValidationError):
            BoardObjectUpdate(image_src=ref)
        with pytest.raises(ValidationError):
            DisplayConfig(image=ref)
        with pytest.raises(ValidationError):
            BoardCreate(name="b1", background_image=ref)
        with pytest.raises(ValidationError):
            BoardUpdate(background_image=ref)

    @pytest.mark.parametrize("ref", ["server.svg", "std_medium.png", "my map (1).PNG", None, ""])
    def test_accepts_plain_filenames(self, ref: str | None) -> None:
        BoardObject(id="o1", type="image", image_src=ref, display={"image": ref})
        BoardCreate(name="b1", background_image=ref)

    @pytest.mark.parametrize("ref", _UNSAFE_ASSET_REFS)
    def test_stored_board_still_loads_without_the_ref(self, ref: str) -> None:
        data: dict[str, object] = {
            "name": "b1",
            "background_image": ref,
            "objects": [{"id": "o1", "type": "image", "image_src": ref, "display": {"image": ref}}],
        }
        _sanitize_legacy_data(data)
        cfg = BoardConfig.model_validate(data)
        assert cfg.background_image is None
        assert cfg.objects[0].image_src is None
        assert cfg.objects[0].display is not None
        assert cfg.objects[0].display.image is None


class TestUrlTargetNarrowing:
    """Object links may open a new tab or stay in the frame, never replace the whole UI."""

    @pytest.mark.parametrize("target", ["_top", "_parent", "named-frame", "_TOP"])
    def test_folds_frame_escapes_to_blank(self, target: str) -> None:
        assert BoardObject(id="o1", type="host", url_target=target).url_target == "_blank"
        assert BoardObjectUpdate(url_target=target).url_target == "_blank"

    @pytest.mark.parametrize("target", ["_blank", "_self", ""])
    def test_keeps_allowed_targets(self, target: str) -> None:
        assert BoardObject(id="o1", type="host", url_target=target).url_target == target

    def test_update_without_target_stays_unset(self) -> None:
        assert "url_target" not in BoardObjectUpdate().model_dump(exclude_unset=True)


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

    @pytest.mark.parametrize(
        "body",
        [
            pytest.param(b'<iframe src="https://evil.example/"/>', id="iframe"),
            pytest.param(
                b'<x:iframe xmlns:x="http://www.w3.org/1999/xhtml" '
                b'srcdoc="&lt;script&gt;alert(1)&lt;/script&gt;"/>',
                id="foreign-ns-iframe",
            ),
            pytest.param(
                b'<x:object xmlns:x="http://www.w3.org/1999/xhtml" data="https://evil.example/"/>',
                id="foreign-ns-object",
            ),
            pytest.param(
                b'<x:embed xmlns:x="http://www.w3.org/1999/xhtml" src="https://evil.example/"/>',
                id="foreign-ns-embed",
            ),
            pytest.param(
                b'<a><set attributeName="href" to="javascript:alert(1)"/><rect/></a>', id="smil-set"
            ),
            pytest.param(b'<animate attributeName="x"/>', id="animate"),
            pytest.param(b'<animateTransform attributeName="transform"/>', id="animatexf"),
            pytest.param(b"<animateMotion/>", id="animatemotion"),
            pytest.param(b"<handler>alert(1)</handler>", id="handler"),
            pytest.param(b"<SCRIPT>alert(1)</SCRIPT>", id="upper-script"),
            pytest.param(b"<foreignobject/>", id="lower-foreignobject"),
        ],
    )
    def test_rejects_script_capable_elements(self, body: bytes) -> None:
        svg = b'<svg xmlns="http://www.w3.org/2000/svg">' + body + b"</svg>"
        assert is_safe_svg(svg) is False

    @pytest.mark.parametrize(
        "svg",
        [
            pytest.param(
                b'<?xml version="1.0"?><?xml-stylesheet type="text/xsl" href="evil.xsl"?>'
                b'<svg xmlns="http://www.w3.org/2000/svg"/>',
                id="xslt-pi",
            ),
            pytest.param(
                b'<svg xmlns="http://www.w3.org/2000/svg">'
                b'<style>@import url("https://evil.example/x.css");</style></svg>',
                id="style-import",
            ),
            pytest.param(
                b'<svg xmlns="http://www.w3.org/2000/svg">'
                b"<style><x/>rect{fill:url(//evil.example/p)}</style></svg>",
                id="style-tail-url",
            ),
            pytest.param(
                b'<svg xmlns="http://www.w3.org/2000/svg">'
                b'<rect style="fill:url(https://evil.example/p)"/></svg>',
                id="style-attr-url",
            ),
            pytest.param(
                b'<svg xmlns="http://www.w3.org/2000/svg">'
                b'<style>@\\69mport "https://evil.example/x.css";</style></svg>',
                id="style-escaped-import",
            ),
            pytest.param(
                b'<svg xmlns="http://www.w3.org/2000/svg">'
                b'<rect style="fill:url(\\68 ttps://evil.example/p)"/></svg>',
                id="style-escaped-scheme",
            ),
            pytest.param(
                b'<svg xmlns="http://www.w3.org/2000/svg">'
                b'<style>text{content:"/*"} rect{fill:url(https://evil.example/p)}</style></svg>',
                id="style-comment-in-string",
            ),
            pytest.param(
                b'<svg xmlns="http://www.w3.org/2000/svg">'
                b'<rect fill="url(https://evil.example/x.svg#g)"/></svg>',
                id="remote-fill",
            ),
            pytest.param(
                b'<svg xmlns="http://www.w3.org/2000/svg">'
                b'<style>rect{fill:image-set("https://evil.example/t.png" 1x)}</style></svg>',
                id="style-image-set-string",
            ),
            pytest.param(
                b'<svg xmlns="http://www.w3.org/2000/svg">'
                b"<rect style=\"background:-webkit-image-set('//evil.example/t.png' 1x)\"/></svg>",
                id="style-attr-webkit-image-set",
            ),
            pytest.param(
                b'<svg xmlns="http://www.w3.org/2000/svg">'
                b'<style>rect{fill:image-set("a.png" 1x, "https://evil.example/t.png" 2x)}</style>'
                b"</svg>",
                id="style-image-set-second-candidate",
            ),
            pytest.param(
                b'<svg xmlns="http://www.w3.org/2000/svg">'
                # Four backslashes in the CSS decode to two; the URL parser reads //.
                b'<style>rect{fill:url("\\\\\\\\evil.example/p")}</style></svg>',
                id="style-backslash-host",
            ),
            pytest.param(
                b'<svg xmlns="http://www.w3.org/2000/svg">'
                b'<style>rect{fill:url("ht\\9tps://evil.example/p")}</style></svg>',
                id="style-escaped-tab-in-scheme",
            ),
            pytest.param(
                b'<svg xmlns="http://www.w3.org/2000/svg">'
                b'<style>rect{fill:image-set("a;b" 1x, "https://evil.example/t.png" 2x)}</style>'
                b"</svg>",
                id="style-image-set-semicolon-in-string",
            ),
            pytest.param(
                b'<svg xmlns="http://www.w3.org/2000/svg">'
                b'<rect filter="url(//evil.example/f.svg#f)"/></svg>',
                id="remote-filter",
            ),
            pytest.param(
                '<?xml version="1.0" encoding="UTF-16"?>'
                '<?xml-stylesheet type="text/xsl" href="evil.xsl"?>'
                '<svg xmlns="http://www.w3.org/2000/svg"/>'.encode("utf-16"),
                id="utf16-xslt-pi",
            ),
            pytest.param(
                b'<svg xmlns="http://www.w3.org/2000/svg">'
                b'<image href="https://evil.example/track.png"/></svg>',
                id="remote-image",
            ),
            pytest.param(
                b'<svg xmlns="http://www.w3.org/2000/svg" '
                b'xmlns:xlink="http://www.w3.org/1999/xlink">'
                b'<filter><feImage xlink:href="https://evil.example/x"/></filter></svg>',
                id="remote-feimage",
            ),
            pytest.param(
                b'<svg xmlns="http://www.w3.org/2000/svg">'
                b'<a href="java&#9;script:alert(1)"><rect/></a></svg>',
                id="tab-in-scheme",
            ),
            pytest.param(
                b'<svg xmlns="http://www.w3.org/2000/svg">'
                b'<a href="&#1;javascript:alert(1)"><rect/></a></svg>',
                id="leading-control-char",
            ),
        ],
    )
    def test_rejects_external_and_obfuscated_references(self, svg: bytes) -> None:
        assert is_safe_svg(svg) is False

    def test_accepts_local_paint_and_embedded_raster(self) -> None:
        good = (
            b'<?xml version="1.0" encoding="UTF-8"?>'
            b'<svg xmlns="http://www.w3.org/2000/svg">'
            b'<defs><linearGradient id="g"/></defs>'
            b"<style>rect{fill:url(#g)}</style>"
            b'<rect style="fill:url(#g)" fill="url(#g)" mask="url(#g)"/>'
            b'<image href="data:image/png;base64,iVBORw0KGgo="/>'
            b'<a href="https://example.com/"><circle r="1"/></a></svg>'
        )
        assert is_safe_svg(good) is True

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


class TestRadarObjectFilter:
    """Radar all_hosts / all_services boards reuse the dyngroup filter rules."""

    def test_normalises_filter_for_all_hosts(self) -> None:
        view = RadarView(filter="all_hosts", object_filter="Filter: host_name ~ ^fw-")
        assert view.object_filter == "Filter: host_name ~ ^fw-\n"

    def test_blank_filter_becomes_none(self) -> None:
        assert RadarView(filter="all_services", object_filter="  \n ").object_filter is None

    def test_rejects_injected_headers(self) -> None:
        with pytest.raises(ValidationError):
            RadarView(filter="all_hosts", object_filter="Filter: a\\nColumns: name address")

    @pytest.mark.parametrize("group_filter", ["hostgroup", "servicegroup"])
    def test_group_filters_drop_object_filter(self, group_filter: str) -> None:
        view = RadarView(
            filter=group_filter, filter_value="web", object_filter="Filter: host_name ~ ^fw-"
        )
        assert view.object_filter is None


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
        cmd = _build_action_command(body, self._ADMIN)
        assert "\n" not in cmd and "\r" not in cmd
        assert cmd.startswith("SCHEDULE_FORCED_HOST_CHECK;host INJECT x;")

    def test_builder_sanitizes_simple_service_command(self) -> None:
        body = ServiceActionRequest.model_construct(
            action="force_check", host_name="h\nx", service_description="s;y"
        )
        cmd = _build_action_command(body, self._ADMIN)
        assert "\n" not in cmd and "\r" not in cmd
        assert cmd.startswith("SCHEDULE_FORCED_SVC_CHECK;h x;s y;")


class TestMetricHistoryScope:
    """The automation-credentialed REST path must not reach objects the viewer can't see."""

    @staticmethod
    def _rest_connection() -> LivestatusConnection:
        return LivestatusConnection(
            socket_path="/dev/null",
            checkmk_url="https://cmk.example/site/check_mk",
            automation_user="automation",
            automation_secret="secret",
        )

    @pytest.mark.asyncio
    async def test_invisible_object_skips_rest_lookups(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        conn = self._rest_connection()
        rest_calls: list[str] = []

        async def _no_rows(_query: str) -> list[list[object]]:
            return []

        async def _rest(*_args: object, **_kwargs: object) -> list[str]:
            rest_calls.append("rest")
            return ["leaked"]

        monkeypatch.setattr(conn, "_query", _no_rows)
        monkeypatch.setattr(conn, "_get_cmk_metric_names", _rest)
        result = await conn.get_metric_history("foreign-host", "CPU load", 0, 3600)
        assert result.series == {}
        assert rest_calls == []

    @pytest.mark.asyncio
    async def test_failed_lookup_fails_closed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        conn = self._rest_connection()

        async def _boom(_query: str) -> list[list[object]]:
            raise OSError("livestatus down")

        async def _unexpected(*_args: object, **_kwargs: object) -> MetricHistoryResult:
            raise AssertionError("history fetched without a visibility check")

        monkeypatch.setattr(conn, "_query", _boom)
        monkeypatch.setattr(conn, "_fetch_cmk_graph_history", _unexpected)
        assert (await conn.get_metric_history("h", None, 0, 3600)).series == {}

    @pytest.mark.asyncio
    async def test_visible_object_passes_its_perf_data(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        conn = self._rest_connection()
        seen: list[str] = []

        async def _rows(_query: str) -> list[list[object]]:
            return [["load1=0.5;;;0;", "check_mk-cpu.loads"]]

        async def _history(
            _host: str, _service: str | None, perf_data: str, _start: int, _end: int
        ) -> MetricHistoryResult:
            seen.append(perf_data)
            return MetricHistoryResult()

        monkeypatch.setattr(conn, "_query", _rows)
        monkeypatch.setattr(conn, "_fetch_cmk_graph_history", _history)
        await conn.get_metric_history("h", "CPU load", 0, 3600)
        assert seen == ["load1=0.5;;;0;"]
