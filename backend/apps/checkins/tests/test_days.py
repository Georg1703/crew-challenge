"""The pure day rules, on a challenge running 1-30 November 2026 (1 November is a Sunday)."""

from datetime import date
from decimal import Decimal

import pytest

from apps.challenges.models import Challenge
from apps.checkins import days
from apps.checkins.days import DayState

NOV = days.Span(first=date(2026, 11, 1), last=date(2026, 11, 30))


def challenge(**fields) -> Challenge:
    defaults = {
        "title": "Test",
        "measure": "check",
        "frequency": "daily",
        "weekdays": 0,
        "target_scope": "none",
        "start_date": date(2026, 11, 1),
        "end_date": date(2026, 11, 30),
    }
    return Challenge(**{**defaults, **fields})


def d(day: int) -> date:
    return date(2026, 11, day)


def record(done=(), partial=(), amounts=None) -> days.Record:
    return days.Record(
        done={d(n) for n in done}, partial={d(n) for n in partial}, amounts=amounts or {}
    )


def test_span_runs_until_someone_leaves():
    c = challenge()
    assert days.span(c, None) == NOV
    assert days.span(c, d(20)) == days.Span(d(1), d(20))
    assert NOV.days(date(2026, 10, 30), d(2)) == [d(1), d(2)]
    assert NOV.days(d(5), d(4)) == []


def test_due_days_per_frequency():
    weekdays = challenge(frequency="weekdays", weekdays=0b0010101)  # Mon, Wed, Fri
    assert [days.is_due(weekdays, d(n)) for n in (2, 3, 4)] == [True, False, True]
    assert days.is_due(challenge(), d(3))
    assert not days.is_due(challenge(frequency="times_per_week", times=3), d(3))


@pytest.mark.parametrize(
    ("fields", "total", "counted"),
    [
        ({}, None, True),
        ({"measure": "abstain"}, None, True),
        ({"measure": "quantity", "unit": "km"}, Decimal(0), False),
        ({"measure": "quantity", "unit": "km"}, Decimal("0.5"), True),
        (
            {"measure": "quantity", "target_scope": "per_check_in", "target_value": Decimal(20)},
            Decimal(19),
            False,
        ),
        (
            {"measure": "quantity", "target_scope": "per_check_in", "target_value": Decimal(20)},
            Decimal(20),
            True,
        ),
        (
            {"measure": "quantity", "target_scope": "per_week", "target_value": Decimal(100)},
            Decimal(1),
            True,
        ),
    ],
)
def test_when_a_day_counts(fields, total, counted):
    assert days.counts(challenge(**fields), total) is counted


def test_day_states_of_a_daily_challenge():
    c, r = challenge(), record(done=[8], partial=[10, 9])
    today = d(10)
    assert days.state(c, NOV, r, d(8), today) == DayState.DONE
    assert days.state(c, NOV, r, d(9), today) == DayState.MISSED  # a partial past day is missed
    assert days.state(c, NOV, r, d(10), today) == DayState.PARTIAL
    assert days.state(c, NOV, record(), today, today) == DayState.TODO
    assert days.state(c, NOV, r, d(11), today) == DayState.FUTURE
    assert days.state(c, NOV, r, date(2026, 10, 31), today) == DayState.OUTSIDE


def test_day_states_of_weekday_and_flexible_challenges():
    weekdays = challenge(frequency="weekdays", weekdays=0b0000001)  # Mondays
    today = d(10)  # Tuesday
    assert days.state(weekdays, NOV, record(), d(9), today) == DayState.MISSED
    assert days.state(weekdays, NOV, record(), d(8), today) == DayState.NOT_DUE
    assert days.state(weekdays, NOV, record(), today, today) == DayState.NOT_DUE
    flexible = challenge(frequency="times_per_week", times=3)
    assert days.state(flexible, NOV, record(), today, today) == DayState.OPEN
    assert days.state(flexible, NOV, record(), d(9), today) == DayState.NOT_DUE


def test_daily_streak_counts_back_and_today_never_breaks_it():
    c = challenge()
    assert days.streak(c, NOV, record(done=[7, 8, 9]), d(10)) == 3  # today still open
    assert days.streak(c, NOV, record(done=[7, 8, 9, 10]), d(10)) == 4
    assert days.streak(c, NOV, record(done=[7, 9]), d(10)) == 1  # 8 was missed
    assert days.streak(c, NOV, record(), d(10)) == 0
    after = days.Span(d(1), d(5))  # left on the 5th
    assert days.streak(c, after, record(done=[3, 4, 5]), d(10)) == 3


def test_weekday_streak_skips_days_that_are_not_due():
    c = challenge(frequency="weekdays", weekdays=0b0010101)  # Mon, Wed, Fri
    # Mon 2, Wed 4, Fri 6, Mon 9 done; Tue 10 is not due.
    assert days.streak(c, NOV, record(done=[2, 4, 6, 9]), d(10)) == 4


def test_weekly_streak_and_partial_weeks():
    c = challenge(frequency="times_per_week", times=3)
    # Week of 26 Oct - 1 Nov has only Sunday 1 Nov: it asks for once.
    assert days.week_quota(c, NOV, d(1)) == 1
    assert days.week_quota(c, NOV, d(30)) == 1  # Monday 30 Nov alone
    r = record(done=[1, 2, 3, 4])  # week 1: 1/1, week 2: 3/3
    assert days.streak(c, NOV, r, d(10)) == 2  # the current week (9-15) is still open
    assert days.streak(c, NOV, record(done=[1, 9, 10, 11]), d(11)) == 1  # week 2 missed
    assert days.streak(challenge(frequency="once"), NOV, r, d(10)) is None


def test_progress_toward_week_period_and_targets():
    today = d(10)
    weekly = days.progress(challenge(frequency="times_per_week", times=3), NOV, record([9]), today)
    assert weekly == days.Progress("days", Decimal(1), Decimal(3))
    period = days.progress(
        challenge(frequency="times_per_period", times=12), NOV, record([1, 9]), today
    )
    assert period == days.Progress("days", Decimal(2), Decimal(12))
    once = days.progress(challenge(frequency="once"), NOV, record([3, 9]), today)
    assert once == days.Progress("days", Decimal(1), Decimal(1))
    amounts = {d(8): Decimal(30), d(9): Decimal(5), d(10): Decimal(7)}
    per_week = challenge(measure="quantity", target_scope="per_week", target_value=Decimal(50))
    assert days.progress(per_week, NOV, record(amounts=amounts), today) == days.Progress(
        "amount", Decimal(12), Decimal(50)
    )
    per_period = challenge(measure="quantity", target_scope="per_period", target_value=Decimal(90))
    period_total = days.progress(per_period, NOV, record(amounts=amounts), today)
    assert period_total is not None
    assert period_total.done == Decimal(42)
    assert days.progress(challenge(), NOV, record(), today) is None


def test_ring_segments():
    today = d(10)
    assert days.settled_today(challenge(), NOV, record(done=[10]), today) is True
    assert days.settled_today(challenge(), NOV, record(), today) is False
    monday_only = challenge(frequency="weekdays", weekdays=0b0000001)
    assert days.settled_today(monday_only, NOV, record(), today) is None
    weekly = challenge(frequency="times_per_week", times=2)
    assert days.settled_today(weekly, NOV, record(done=[9]), today) is False
    assert days.settled_today(weekly, NOV, record(done=[9, 10]), today) is True
    assert days.settled_today(weekly, NOV, record(done=[8, 9]), d(9)) is True  # quota met
    assert days.settled_today(challenge(), days.Span(d(1), d(5)), record(), today) is None


def test_longest_streak_of_fixed_days():
    c = challenge()
    assert days.longest_streak(c, NOV, record(done=[1, 2, 3, 5, 6]), d(10)) == 3
    assert days.longest_streak(c, NOV, record(done=[7, 8, 9]), d(10)) == 3  # today still open
    assert days.longest_streak(c, NOV, record(done=[8, 9, 10]), d(10)) == 3
    assert days.longest_streak(c, NOV, record(), d(10)) == 0
    left = days.Span(d(1), d(4))  # left on the 4th: later days do not count
    assert days.longest_streak(c, left, record(done=[3, 4, 5, 6, 7]), d(10)) == 2
    weekdays = challenge(frequency="weekdays", weekdays=0b0010101)  # Mon, Wed, Fri
    assert days.longest_streak(weekdays, NOV, record(done=[2, 4, 6, 9]), d(10)) == 4


def test_longest_streak_crosses_the_clock_change():
    autumn = challenge(start_date=date(2026, 10, 20), end_date=date(2026, 11, 5))
    part = days.Span(date(2026, 10, 20), date(2026, 11, 5))
    done = {date(2026, 10, n) for n in range(23, 32)} | {d(1)}  # 23 Oct - 1 Nov, over 25 Oct
    assert days.longest_streak(autumn, part, days.Record(done=done), d(3)) == 10


def test_longest_streak_of_weeks_and_none_for_counts():
    c = challenge(frequency="times_per_week", times=3)
    r = record(done=[1, 2, 3, 4, 16, 17, 18])  # weeks 1-2 met, week 3 missed, week 4 met
    assert days.longest_streak(c, NOV, r, d(20)) == 2
    assert days.longest_streak(c, NOV, record(done=[1]), d(3)) == 1  # this week still open
    assert days.longest_streak(challenge(frequency="once"), NOV, r, d(20)) is None
