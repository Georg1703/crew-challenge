"""Which windows a challenge is judged in, and what each one needs (pure, no database)."""

from datetime import date
from decimal import Decimal

import pytest

from apps.challenges.models import Challenge
from apps.challenges.windows import Window, counts_on, window_at, windows


def challenge(start: date, end: date, *, period_start: date | None = None, **fields) -> Challenge:
    defaults = {"title": "Test", "measure": "check", "frequency": "daily", "target_scope": "none"}
    return Challenge(
        **{**defaults, **fields},
        period_start=period_start or start,
        start_date=start,
        end_date=end,
    )


OCT_1, OCT_31 = date(2026, 10, 1), date(2026, 10, 31)  # October 2026 starts on a Thursday


def needs(c: Challenge, first: date, last: date) -> list[tuple[str, str, Decimal]]:
    return [(w.first.isoformat(), w.last.isoformat(), w.need) for w in windows(c, first, last)]


def test_every_day_is_a_window_and_chosen_days_only_count_on_those_days():
    daily = challenge(OCT_1, OCT_31)
    assert len(windows(daily, OCT_1, OCT_31)) == 31
    mwf = challenge(OCT_1, OCT_31, frequency="weekdays", weekdays=0b0010101)  # Mon, Wed, Fri
    days = [w.first.day for w in windows(mwf, OCT_1, date(2026, 10, 11))]
    assert days == [2, 5, 7, 9]
    assert [counts_on(mwf, date(2026, 10, n)) for n in (5, 6, 7)] == [True, False, True]
    assert counts_on(challenge(OCT_1, OCT_31, frequency="times_per_week", times=3), OCT_1)


def test_weeks_run_monday_to_sunday_and_cut_weeks_ask_for_less():
    weekly = challenge(OCT_1, OCT_31, frequency="times_per_week", times=3)
    assert needs(weekly, OCT_1, OCT_31) == [
        ("2026-10-01", "2026-10-04", 2),  # Thu-Sun: 3 x 4/7 = 1.7
        ("2026-10-05", "2026-10-11", 3),
        ("2026-10-12", "2026-10-18", 3),
        ("2026-10-19", "2026-10-25", 3),
        ("2026-10-26", "2026-10-31", 3),  # Mon-Sat: 3 x 6/7 = 2.6
    ]
    first = windows(weekly, OCT_1, OCT_31)[0]
    assert first == Window(OCT_1, date(2026, 10, 4), Decimal(2), Decimal(3))


def test_leaving_mid_week_cuts_the_last_window():
    weekly = challenge(OCT_1, OCT_31, frequency="times_per_week", times=3)
    last = windows(weekly, OCT_1, date(2026, 10, 21))[-1]  # left on Wednesday the 21st
    assert (last.first, last.last, last.need) == (date(2026, 10, 19), date(2026, 10, 21), 1)


def test_a_window_that_would_ask_for_nothing_is_not_judged():
    weekly = challenge(date(2026, 11, 1), date(2026, 11, 30), frequency="times_per_week", times=3)
    found = windows(weekly, date(2026, 11, 1), date(2026, 11, 30))
    # Sunday 1 Nov alone (3 x 1/7 = 0.4) and Monday 30 Nov alone round to nothing.
    assert (found[0].first, found[-1].last) == (date(2026, 11, 2), date(2026, 11, 29))
    assert window_at(weekly, date(2026, 11, 1), date(2026, 11, 30), date(2026, 11, 1)) is None


def test_weeks_cross_months_and_years_and_february_has_whole_weeks():
    winter = challenge(date(2026, 12, 1), date(2027, 1, 31), frequency="times_per_week", times=3)
    crossing = window_at(winter, date(2026, 12, 1), date(2027, 1, 31), date(2027, 1, 1))
    assert crossing == Window(date(2026, 12, 28), date(2027, 1, 3), Decimal(3), Decimal(3))
    february = challenge(date(2027, 2, 1), date(2027, 2, 28), frequency="times_per_week", times=3)
    assert [w.need for w in windows(february, date(2027, 2, 1), date(2027, 2, 28))] == [3] * 4


def test_amounts_scale_to_one_decimal():
    km = challenge(
        OCT_1, OCT_31, measure="quantity", target_scope="per_week", target_value=Decimal(50)
    )
    assert [w.need for w in windows(km, OCT_1, OCT_31)] == [
        Decimal("28.6"),
        Decimal(50),
        Decimal(50),
        Decimal(50),
        Decimal("42.9"),
    ]


def test_a_late_start_scales_the_whole_period_and_halves_round_up():
    late = challenge(
        date(2026, 10, 15), OCT_31, period_start=OCT_1, frequency="times_per_period", times=8
    )
    assert windows(late, date(2026, 10, 15), OCT_31) == [
        Window(date(2026, 10, 15), OCT_31, Decimal(4), Decimal(8))  # 8 x 17/31 = 4.4
    ]
    half = challenge(
        date(2026, 11, 6),
        date(2026, 11, 10),
        period_start=date(2026, 11, 1),
        frequency="times_per_period",
        times=1,
    )
    assert windows(half, date(2026, 11, 6), date(2026, 11, 10))[0].need == 1  # 1 x 5/10 = 0.5


@pytest.mark.parametrize(
    ("fields", "need"),
    [
        ({"frequency": "once"}, Decimal(1)),
        ({"frequency": "times_per_period", "times": 12}, Decimal(12)),
        (
            {"measure": "quantity", "target_scope": "per_period", "target_value": Decimal(90)},
            Decimal(90),
        ),
    ],
)
def test_whole_period_challenges_have_one_window(fields, need):
    c = challenge(OCT_1, OCT_31, **fields)
    assert windows(c, OCT_1, OCT_31) == [Window(OCT_1, OCT_31, need, need)]
