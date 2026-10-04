"""Calendar periods a round can cover. v1 uses months; weeks and custom ranges come later.

Pure functions on crew-local dates (no time zones here: callers pass `clock.crew_today(crew)`).
"""

from __future__ import annotations

import calendar
from datetime import date, timedelta


def month_of(day: date) -> tuple[date, date]:
    """First and last day of the month that contains `day`."""
    last = calendar.monthrange(day.year, day.month)[1]
    return day.replace(day=1), day.replace(day=last)


def next_month_of(day: date) -> tuple[date, date]:
    """First and last day of the month after the one that contains `day`."""
    _, last = month_of(day)
    return month_of(last + timedelta(days=1))
