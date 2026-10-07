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
        "period_start": date(2026, 11, 1),
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


def test_due_days_are_the_counting_days_of_day_windows():
    weekdays = challenge(on_days=0b0010101)  # Mon, Wed, Fri
    assert [days.is_due(weekdays, d(n)) for n in (2, 3, 4)] == [True, False, True]
    assert days.is_due(challenge(), d(3))
    assert not days.is_due(challenge(window="week", need_value=3), d(3))


@pytest.mark.parametrize(
    ("fields", "total", "counted"),
    [
        ({}, None, True),
        ({"measure": "abstain"}, None, True),
        ({"measure": "quantity", "unit": "km"}, Decimal(0), False),
        ({"measure": "quantity", "unit": "km"}, Decimal("0.5"), True),
        (
            {"measure": "quantity", "day_min": Decimal(20)},
            Decimal(19),
            False,
        ),
        (
            {"measure": "quantity", "day_min": Decimal(20)},
            Decimal(20),
            True,
        ),
        (
            {
                "measure": "quantity",
                "window": "week",
                "need_kind": "amount",
                "need_value": Decimal(100),
            },
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
    weekdays = challenge(on_days=0b0000001)  # Mondays
    today = d(10)  # Tuesday
    assert days.state(weekdays, NOV, record(), d(9), today) == DayState.MISSED
    assert days.state(weekdays, NOV, record(), d(8), today) == DayState.NOT_DUE
    assert days.state(weekdays, NOV, record(), today, today) == DayState.NOT_DUE
    flexible = challenge(window="week", need_value=3)
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
    c = challenge(on_days=0b0010101)  # Mon, Wed, Fri
    # Mon 2, Wed 4, Fri 6, Mon 9 done; Tue 10 is not due.
    assert days.streak(c, NOV, record(done=[2, 4, 6, 9]), d(10)) == 4


def test_weekly_streak_counts_met_weeks_and_skips_the_open_one():
    c = challenge(window="week", need_value=3)
    # Sunday 1 Nov alone asks for 3 x 1/7, rounded to nothing: it isn't judged.
    r = record(done=[1, 2, 3, 4])  # week 2-8: 3 of 3
    assert days.streak(c, NOV, r, d(10)) == 1  # the current week (9-15) is still open
    assert days.streak(c, NOV, record(done=[1, 9, 10, 11]), d(11)) == 1  # week 2-8 missed
    assert days.streak(challenge(window="period"), NOV, r, d(10)) is None


def test_progress_toward_week_period_and_targets():
    today = d(10)
    weekly = days.progress(challenge(window="week", need_value=3), NOV, record([9]), today)
    assert weekly == days.Progress("days", Decimal(1), Decimal(3))
    period = days.progress(challenge(window="period", need_value=12), NOV, record([1, 9]), today)
    assert period == days.Progress("days", Decimal(2), Decimal(12))
    once = days.progress(challenge(window="period"), NOV, record([3, 9]), today)
    assert once == days.Progress("days", Decimal(2), Decimal(1))  # what was done, not capped
    amounts = {d(8): Decimal(30), d(9): Decimal(5), d(10): Decimal(7)}
    per_week = challenge(
        measure="quantity", window="week", need_kind="amount", need_value=Decimal(50)
    )
    assert days.progress(per_week, NOV, record(amounts=amounts), today) == days.Progress(
        "amount", Decimal(12), Decimal(50)
    )
    per_period = challenge(
        measure="quantity", window="period", need_kind="amount", need_value=Decimal(90)
    )
    period_total = days.progress(per_period, NOV, record(amounts=amounts), today)
    assert period_total is not None
    assert period_total.done == Decimal(42)
    assert days.progress(challenge(), NOV, record(), today) is None


def test_ring_segments():
    today = d(10)
    assert days.settled_today(challenge(), NOV, record(done=[10]), today) is True
    assert days.settled_today(challenge(), NOV, record(), today) is False
    monday_only = challenge(on_days=0b0000001)
    assert days.settled_today(monday_only, NOV, record(), today) is None
    weekly = challenge(window="week", need_value=2)
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
    weekdays = challenge(on_days=0b0010101)  # Mon, Wed, Fri
    assert days.longest_streak(weekdays, NOV, record(done=[2, 4, 6, 9]), d(10)) == 4


def test_longest_streak_crosses_the_clock_change():
    autumn = challenge(
        period_start=date(2026, 10, 20), start_date=date(2026, 10, 20), end_date=date(2026, 11, 5)
    )
    part = days.Span(date(2026, 10, 20), date(2026, 11, 5))
    done = {date(2026, 10, n) for n in range(23, 32)} | {d(1)}  # 23 Oct - 1 Nov, over 25 Oct
    assert days.longest_streak(autumn, part, days.Record(done=done), d(3)) == 10


def test_longest_streak_of_weeks_and_none_for_counts():
    c = challenge(window="week", need_value=3)
    r = record(done=[2, 3, 4, 16, 17, 18, 23, 24, 25])  # 2-8 met, 9-15 missed, then met
    assert days.longest_streak(c, NOV, r, d(26)) == 2
    assert days.longest_streak(c, NOV, record(done=[1]), d(3)) == 0  # this week still open
    assert days.longest_streak(challenge(window="period"), NOV, r, d(20)) is None


# Daily and chosen-day challenges as they behaved before the window rules: they must not change.
# One letter a day for 1-30 November: Done, Partial, Todo, Missed, Not due, Future, X outside.
LETTERS = {
    "done": "D",
    "partial": "P",
    "todo": "T",
    "missed": "M",
    "not_due": "N",
    "future": "F",
    "outside": "X",
}
MWF = {"on_days": 0b0010101}


@pytest.mark.parametrize(
    ("fields", "done", "partial", "left", "today", "states", "streak", "longest", "settled"),
    [
        ({}, range(1, 10), [], None, d(10), "D" * 9 + "T" + "F" * 20, 9, 9, False),
        ({}, range(1, 11), [], None, d(10), "D" * 10 + "F" * 20, 10, 10, True),
        ({}, [1, 2, 3, 5, 6, 8, 9], [4], None, d(10), "DDDMDDMDDT" + "F" * 20, 2, 3, False),
        ({}, [7, 8, 9], [10], None, d(10), "MMMMMMDDDP" + "F" * 20, 3, 3, False),
        ({}, [1, 2, 3, 5, 6], [], 6, d(10), "DDDMDD" + "X" * 24, 2, 3, None),
        ({}, [], [], None, date(2026, 10, 28), "F" * 30, 0, 0, None),
        (
            {},
            [n for n in range(1, 31) if n != 28],
            [],
            None,
            date(2026, 12, 3),
            "D" * 27 + "MDD",
            2,
            27,
            None,
        ),
        ({}, [], [], None, d(10), "M" * 9 + "T" + "F" * 20, 0, 0, False),
        ({}, [2, 4, 6, 9, 11], [], None, d(11), "MDMDMDMMDMD" + "F" * 19, 1, 1, True),
        (MWF, [2, 4, 6, 9], [], None, d(10), "NDNDNDNNDN" + "F" * 20, 4, 4, None),
        (MWF, range(1, 11), [], None, d(10), "NDNDNDNNDN" + "F" * 20, 4, 4, None),
        (MWF, [2, 6, 9], [4], None, d(10), "NDNMNDNNDN" + "F" * 20, 2, 2, None),
        (MWF, [9], [], None, d(10), "NMNMNMNNDN" + "F" * 20, 1, 1, None),
        (MWF, [2, 6], [], 6, d(10), "NDNMND" + "X" * 24, 1, 1, None),
        (MWF, [], [], None, date(2026, 10, 28), "F" * 30, 0, 0, None),
        (
            MWF,
            [n for n in range(1, 31) if n != 28],
            [],
            None,
            date(2026, 12, 3),
            "NDNDNDNNDNDNDNNDNDNDNNDNDNDNND",
            13,
            13,
            None,
        ),
        (MWF, [], [], None, d(10), "NMNMNMNNMN" + "F" * 20, 0, 0, None),
        (MWF, [2, 4, 6, 9, 11], [], None, d(11), "NDNDNDNNDND" + "F" * 19, 5, 5, True),
    ],
)
def test_daily_and_chosen_day_rules_are_unchanged(
    fields, done, partial, left, today, states, streak, longest, settled
):
    c = challenge(**fields)
    part = days.span(c, d(left) if left else None)
    due = [n for n in done if days.is_due(c, d(n))]  # check-ins are refused on other days
    r = record(done=due, partial=[n for n in partial if days.is_due(c, d(n))])
    assert "".join(LETTERS[days.state(c, part, r, d(n), today)] for n in range(1, 31)) == states
    assert days.streak(c, part, r, today) == streak
    assert days.longest_streak(c, part, r, today) == longest
    assert days.settled_today(c, part, r, today) is settled
    assert days.progress(c, part, r, today) is None


def test_a_window_is_judged_on_the_days_up_to_today():
    weekly = challenge(window="week", need_value=3)
    week = days.windows.window_at(weekly, d(1), d(30), d(10))
    assert week is not None  # Monday 9 - Sunday 15
    verdict = days.judge(weekly, week, record(done=[9, 10, 11]), d(11))
    assert (verdict.state, verdict.done, verdict.short) == ("met", 3, 0)  # met before it ends
    assert days.judge(weekly, week, record(done=[9]), d(15)).state == "open"  # Sunday: still open
    late = days.judge(weekly, week, record(done=[9]), d(16))
    assert (late.state, late.done, late.need, late.short) == ("failed", 1, 3, 2)
    assert days.judge(weekly, week, record(), d(8)).state == "future"


def test_a_total_is_judged_on_the_amounts_of_its_days():
    km = challenge(measure="quantity", window="week", need_kind="amount", need_value=Decimal(50))
    week = days.windows.window_at(km, d(1), d(30), d(10))
    assert week is not None
    amounts = {d(8): Decimal(30), d(9): Decimal(20), d(14): Decimal(21)}  # the 8th is last week
    verdict = days.judge(km, week, record(amounts=amounts), d(16))
    assert (verdict.state, verdict.done, verdict.short) == ("failed", Decimal(41), Decimal(9))
