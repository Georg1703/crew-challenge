"""0008: every old rule maps to a window and a need, and back (tests run without migrations, so
the mapping functions are checked here and the migration itself on a real database by hand)."""

import importlib
from decimal import Decimal
from types import SimpleNamespace

import pytest

fill = importlib.import_module("apps.challenges.migrations.0008_fill_challenge_rules")

OLD_DEFAULTS = {"weekdays": 0, "times": None, "target_scope": "none", "target_value": None}
NEW_DEFAULTS = {"on_days": 0, "need_kind": "count", "need_value": 1, "day_min": None}
FIELDS = ("window", "on_days", "need_kind", "need_value", "day_min")


def applied(old: dict) -> tuple:
    """The new fields of a row with these old fields, as the migration sets them."""
    rule = {**NEW_DEFAULTS, **fill.rule(SimpleNamespace(**{**OLD_DEFAULTS, **old}))}
    return tuple(rule[f] for f in FIELDS)


@pytest.mark.parametrize(
    ("old", "new"),
    [
        ({"frequency": "daily"}, ("day", 0, "count", 1, None)),
        ({"frequency": "weekdays", "weekdays": 21}, ("day", 21, "count", 1, None)),
        ({"frequency": "times_per_week", "times": 3}, ("week", 0, "count", 3, None)),
        ({"frequency": "times_per_period", "times": 10}, ("period", 0, "count", 10, None)),
        ({"frequency": "once"}, ("period", 0, "count", 1, None)),
        (
            {"frequency": "daily", "target_scope": "per_check_in", "target_value": 20},
            ("day", 0, "count", 1, 20),
        ),
        (
            {"frequency": "daily", "target_scope": "per_week", "target_value": 50},
            ("week", 0, "amount", 50, None),
        ),
        (
            {"frequency": "times_per_week", "times": 2, "target_scope": "per_period"}
            | {"target_value": 200},
            ("period", 0, "amount", 200, None),
        ),
    ],
)
def test_old_rules_become_a_window_and_a_need(old, new):
    assert applied(old) == new


@pytest.mark.parametrize(
    "new",
    [
        ("day", 0, "count", 1, None),
        ("day", 21, "count", 1, None),
        ("day", 0, "count", 1, Decimal(20)),
        ("week", 0, "count", 3, None),
        ("period", 0, "count", 10, None),
        ("period", 0, "count", 1, None),
        ("week", 0, "amount", Decimal(30), None),
        ("period", 0, "amount", Decimal(200), None),
    ],
)
def test_a_new_rule_written_back_reads_the_same(new):
    row = SimpleNamespace(**dict(zip(FIELDS, new, strict=True)))
    assert applied(fill.old_fields(row)) == new
