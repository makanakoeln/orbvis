"""Unit tests for the CMK-version-agnostic site_config helpers."""

from __future__ import annotations

from app.integrations.checkmk_sites import (
    _encode_socket_for_livestatus,
    _filter_enabled,
    _is_single_local_site,
    _site_config_for_livestatus,
)

LIVESTATUS_SOCK = "/omd/sites/test/tmp/run/live"


def test_filter_enabled_drops_disabled() -> None:
    raw = {
        "a": {"socket": ("local", None)},
        "b": {"socket": ("local", None), "disabled": True},
        "c": {"socket": ("local", None), "disabled": False},
    }
    out = _filter_enabled(raw)
    assert set(out) == {"a", "c"}


def test_filter_enabled_returns_copies() -> None:
    raw = {"a": {"socket": ("local", None), "alias": "A"}}
    out = _filter_enabled(raw)
    out["a"]["alias"] = "X"
    assert raw["a"]["alias"] == "A"


def test_is_single_local_site_empty() -> None:
    assert _is_single_local_site({}, LIVESTATUS_SOCK) is True


def test_is_single_local_site_multiple() -> None:
    sites = {
        "a": {"socket": ("local", None)},
        "b": {"socket": ("local", None)},
    }
    assert _is_single_local_site(sites, LIVESTATUS_SOCK) is False


def test_is_single_local_site_one_local() -> None:
    sites = {"a": {"socket": ("local", None)}}
    assert _is_single_local_site(sites, LIVESTATUS_SOCK) is True


def test_is_single_local_site_unix_matching_path() -> None:
    sites = {"a": {"socket": ("unix", {"path": LIVESTATUS_SOCK})}}
    assert _is_single_local_site(sites, LIVESTATUS_SOCK) is True


def test_is_single_local_site_unix_other_path() -> None:
    sites = {"a": {"socket": ("unix", {"path": "/some/other/socket"})}}
    assert _is_single_local_site(sites, LIVESTATUS_SOCK) is False


def test_is_single_local_site_remote_tcp() -> None:
    sites = {"a": {"socket": ("tcp", {"address": ("10.0.0.1", 6557), "tls": ("plain_text", {})})}}
    assert _is_single_local_site(sites, LIVESTATUS_SOCK) is False


def test_encode_socket_local() -> None:
    assert (
        _encode_socket_for_livestatus("s", {"socket": ("local", None)}, LIVESTATUS_SOCK)
        == f"unix:{LIVESTATUS_SOCK}"
    )


def test_encode_socket_unix() -> None:
    spec = {"socket": ("unix", {"path": "/x"})}
    assert _encode_socket_for_livestatus("s", spec, LIVESTATUS_SOCK) == "unix:/x"


def test_encode_socket_tcp() -> None:
    spec = {
        "socket": ("tcp", {"address": ("1.2.3.4", 6557), "tls": ("plain_text", {})}),
    }
    assert _encode_socket_for_livestatus("s", spec, LIVESTATUS_SOCK) == "tcp:1.2.3.4:6557"


def test_encode_socket_proxy() -> None:
    spec = {"socket": ("local", None), "proxy": {}}
    assert (
        _encode_socket_for_livestatus("remote", spec, LIVESTATUS_SOCK)
        == f"unix:{LIVESTATUS_SOCK}proxy/remote"
    )


def test_site_config_includes_tls_for_tcp() -> None:
    spec = {
        "socket": ("tcp", {"address": ("1.2.3.4", 6557), "tls": ("plain_text", {})}),
        "alias": "Remote",
    }
    out = _site_config_for_livestatus("r", spec, LIVESTATUS_SOCK)
    assert out["tls"] == ("plain_text", {})
    assert out["socket"] == "tcp:1.2.3.4:6557"
    assert out["alias"] == "Remote"
