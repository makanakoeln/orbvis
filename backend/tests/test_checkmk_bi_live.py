"""Live tests for the in-process cmk.bi integration.

These run ONLY inside an OMD site environment (CHECKMK_OMD_ROOT set, cmk.bi
importable, livestatus socket reachable) — everywhere else every test skips.
On a populated test site:

    # Run the file from outside backend/tests so conftest.py (needs the dev
    # test deps) is not loaded; SECRET_KEY satisfies the production settings.
    cp backend/tests/test_checkmk_bi_live.py /tmp/
    sudo -iu <SITE> bash -c 'CHECKMK_OMD_ROOT=$OMD_ROOT CHECKMK_SITE=$OMD_SITE \\
        SECRET_KEY=$(openssl rand -hex 32) PYTHONPATH=/path/to/orbvis/backend \\
        $OMD_ROOT/var/orbvis/venv/bin/python3 -m pytest /tmp/test_checkmk_bi_live.py -v'

The dev-suite counterpart (fallback paths, scoped gates with fakes) lives in
test_checkmk_integration.py; this module covers the compile → compute → tree
pipeline that only exists with real cmk.bi.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get("CHECKMK_OMD_ROOT"),
    reason="BI live tests need an OMD site (CHECKMK_OMD_ROOT)",
)


@pytest.fixture(scope="module")
def bi():
    from app.integrations import checkmk as cmk_integration

    cmk_integration.setup()
    if not cmk_integration.cmk_bi_available():
        pytest.skip("cmk.bi not importable in this environment")
    return cmk_integration


@pytest.fixture(scope="module")
def query_callback():
    """The same sync callback the production path hands to cmk.bi."""
    from app.connections.livestatus import LivestatusConnection

    omd_root = os.environ["CHECKMK_OMD_ROOT"]
    socket_path = str(Path(omd_root) / "tmp" / "run" / "live")
    if not Path(socket_path).exists():
        pytest.skip(f"livestatus socket not running at {socket_path}")
    connection = LivestatusConnection(socket_path=socket_path)
    return connection._bi_query_sync


@pytest.fixture(scope="module")
def site_id() -> str:
    return os.environ.get("CHECKMK_SITE") or os.environ.get("OMD_SITE", "")


@pytest.fixture(scope="module")
def aggregations(bi, query_callback, site_id) -> list[dict[str, str]]:
    out = bi.cmk_bi_list_aggregations(query_callback, site_id)
    if not out:
        pytest.skip("site has no compiled BI aggregations")
    return out


def test_list_aggregations_returns_resolved_branches(aggregations):
    for entry in aggregations:
        assert entry["id"] == entry["title"]
        assert entry["title"]
        assert "pack_id" in entry
    titles = [e["title"] for e in aggregations]
    assert titles == sorted(titles, key=str.lower)
    # Resolved branch titles, not bi_config templates with placeholders.
    assert not any("$HOSTNAME$" in t for t in titles)


def test_states_compute_for_listed_aggregation(bi, query_callback, site_id, aggregations):
    name = aggregations[0]["title"]
    states = bi.cmk_bi_get_aggregations_states(query_callback, site_id, [name])
    assert name in states
    # cmk.bi integer states: -1 pending … 3 unknown (state 0 is falsy — see
    # reference gotchas — so assert on the type, not truthiness).
    assert isinstance(states[name]["state"], int)
    assert -2 <= int(str(states[name]["state"])) <= 4


def test_states_for_unknown_aggregation_is_empty(bi, query_callback, site_id):
    states = bi.cmk_bi_get_aggregations_states(
        query_callback, site_id, ["no-such-aggregation-orbvis-test"]
    )
    assert states == {}


def test_tree_matches_aggregation_and_truncates_at_depth(bi, query_callback, site_id, aggregations):
    name = aggregations[0]["title"]
    tree = bi.cmk_bi_get_aggregation_tree(query_callback, site_id, name, max_depth=3)
    assert tree is not None
    assert tree["name"] == name
    assert tree["node_type"] in ("bi_aggregator", "bi_leaf")
    assert isinstance(tree["state"], int)

    root_only = bi.cmk_bi_get_aggregation_tree(query_callback, site_id, name, max_depth=0)
    assert root_only is not None
    assert root_only["children"] == []


def test_tree_for_unknown_aggregation_is_none(bi, query_callback, site_id):
    assert (
        bi.cmk_bi_get_aggregation_tree(
            query_callback, site_id, "no-such-aggregation-orbvis-test", max_depth=2
        )
        is None
    )


@pytest.fixture
def blind_callback(query_callback):
    """Delegates to the real callback but reports zero visible hosts —
    deterministically exercises the scoped-visibility gate without needing a
    contact-scoped test user on the site."""

    def cb(query: object, only_sites: object = None, fetch_full_data: bool = False) -> object:
        if str(query).startswith("GET hosts\nColumns: name\n"):
            return []
        return query_callback(query, only_sites, fetch_full_data)

    return cb


def test_scoped_listing_hides_branches_without_visible_hosts(
    bi, blind_callback, site_id, aggregations
):
    assert bi.cmk_bi_list_aggregations(blind_callback, site_id, scoped=True) == []


def test_scoped_tree_denies_invisible_aggregation(bi, blind_callback, site_id, aggregations):
    name = aggregations[0]["title"]
    assert (
        bi.cmk_bi_get_aggregation_tree(blind_callback, site_id, name, max_depth=2, scoped=True)
        is None
    )
