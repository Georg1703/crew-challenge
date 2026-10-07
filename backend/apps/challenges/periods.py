"""Calendar periods a challenge runs in: whole months, Monday-Sunday weeks, or a number of days.

Pure functions on crew-local dates (no time zones here: callers pass `clock.crew_today(crew)`).
"""

from __future__ import annotations

import calendar
from datetime import date, timedelta

from .models import PeriodKind


def dates(first: date, last: date) -> list[date]:
    """Every day from `first` to `last`, both included (none when `last` comes first)."""
    return [first + timedelta(days=n) for n in range((last - first).days + 1)]


def week_of(day: date) -> tuple[date, date]:
    """Monday and Sunday of the week that contains `day`."""
    monday = day - timedelta(days=day.weekday())
    return monday, monday + timedelta(days=6)


def month_of(day: date) -> tuple[date, date]:
    """First and last day of the month that contains `day`."""
    last = calendar.monthrange(day.year, day.month)[1]
    return day.replace(day=1), day.replace(day=last)


def add_months(first: date, months: int) -> date:
    """The first day of the month `months` after the month that starts on `first`."""
    index = first.year * 12 + first.month - 1 + months
    return date(index // 12, index % 12 + 1, 1)


def period_end(kind: str, start: date, length: int) -> date:
    """The last day of `length` months (from the 1st), weeks (from a Monday) or days."""
    if kind == PeriodKind.MONTH:
        return add_months(start, length) - timedelta(days=1)
    if kind == PeriodKind.WEEK:
        return start + timedelta(weeks=length, days=-1)
    if kind == PeriodKind.DAY:
        return start + timedelta(days=length - 1)
    raise ValueError(f"Unknown period kind: {kind!r}")


def scheduled_dates(kind: str, length: int, period_start: date, today: date) -> tuple[date, date]:
    """The first day that counts and the last day of a period starting on `period_start`.

    A period already under way counts from tomorrow.
    """
    start = period_start if today < period_start else today + timedelta(days=1)
    return start, period_end(kind, period_start, length)
