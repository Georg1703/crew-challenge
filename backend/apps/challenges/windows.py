"""The windows a challenge is judged in, and what each one needs.

A window is a stretch of days judged as one unit: a single day, a Monday-Sunday week, a calendar
month, or the whole period. Its need is a number of check-ins (`count`) or a total amount
(`amount`); a window cut short by the period's edges, a late start or leaving asks for less, in
proportion to its days that count. Pure functions on crew-local dates: no database and no clock.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from .models import Challenge
from .periods import add_months, dates, month_of, week_of


@dataclass(frozen=True)
class Window:
    first: date
    last: date
    need: Decimal  # scaled down when the window is cut short
    full_need: Decimal


def counts_on(challenge: Challenge, day: date) -> bool:
    """Whether a check-in on `day` counts at all (chosen weekdays only, when there are some)."""
    return not challenge.on_days or bool(challenge.on_days & (1 << day.weekday()))


def windows(challenge: Challenge, first: date, last: date) -> list[Window]:
    """The windows of the days `first`..`last` (one member's part), oldest first.

    A window that would ask for nothing after scaling is not judged, so it is left out.
    """
    result = []
    for start, end in _whole_windows(challenge, first, last):
        kept_first, kept_last = max(start, first), min(end, last)
        kept = _counting_days(challenge, kept_first, kept_last)
        whole = _counting_days(challenge, start, end)
        if not kept:
            continue
        full_need = Decimal(challenge.need_value)
        need = full_need if kept == whole else _scaled(challenge, full_need, kept, whole)
        if need > 0:
            result.append(Window(kept_first, kept_last, need, full_need))
    return result


def window_at(challenge: Challenge, first: date, last: date, day: date) -> Window | None:
    """The window that `day` belongs to, if it is judged."""
    return next((w for w in windows(challenge, first, last) if w.first <= day <= w.last), None)


def _whole_windows(challenge: Challenge, first: date, last: date) -> list[tuple[date, date]]:
    """Every window touching `first`..`last`, before cutting it to those days."""
    if challenge.window == Challenge.Window.PERIOD:
        assert challenge.period_start is not None
        assert challenge.end_date is not None
        return [(challenge.period_start, challenge.end_date)]
    if challenge.window == Challenge.Window.WEEK:
        monday, _ = week_of(first)
        weeks = (last - monday).days // 7 + 1 if last >= monday else 0
        return [
            (monday + timedelta(weeks=n), monday + timedelta(weeks=n, days=6)) for n in range(weeks)
        ]
    if challenge.window == Challenge.Window.MONTH:
        months, start = [], month_of(first)[0]
        while start <= last:
            months.append(month_of(start))
            start = add_months(start, 1)
        return months
    return [(day, day) for day in dates(first, last)]


def _counting_days(challenge: Challenge, first: date, last: date) -> int:
    return sum(1 for day in dates(first, last) if counts_on(challenge, day))


def _scaled(challenge: Challenge, need: Decimal, kept: int, whole: int) -> Decimal:
    """The need in proportion to the days kept: whole check-ins, or amounts to one decimal."""
    step = Decimal(1) if challenge.need_kind == Challenge.NeedKind.COUNT else Decimal("0.1")
    return (need * kept / whole).quantize(step, rounding=ROUND_HALF_UP)
