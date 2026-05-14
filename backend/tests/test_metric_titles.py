"""Regression tests for metric/graph title cleanup."""

from __future__ import annotations

from app.connections.livestatus import _identity


def test_identity_strips_expression_placeholder():
    raw = 'CPU load average of last 15 minutes _EXPRESSION:{"metric":"load1","scalar":"max"} CPU Cores'
    assert _identity(raw) == "CPU load average of last 15 minutes CPU Cores"


def test_identity_strips_multiple_expressions():
    raw = '_EXPRESSION:{"a":1} foo _EXPRESSION:{"b":2} bar'
    assert _identity(raw) == "foo bar"


def test_identity_passes_clean_titles_through_unchanged():
    assert _identity("CPU load average") == "CPU load average"
