"""The windows a challenge is judged in, and what each one needs.

A window is a stretch of days judged as one unit: a single day, a Monday-Sunday week, or the
whole period. Its need is a number of check-ins (`count`) or a total amount (`amount`); a window
cut short by the period's edges, a late start or leaving asks for less, in proportion to its days
that count. Pure functions on crew-local dates: no database and no clock here.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from .models import Challenge
from .periods import week_of

DAY, WEEK, PERIOD = "day", "week", "period"
COUNT, AMOUNT = "count", "amount"


@dataclass(frozen=True)
class Rule:
    """How a challenge is judged."""

    window: str
    on_days: int  # weekday mask (Monday = 1 ... Sunday = 64); 0 = every day
    need_kind: str
    need_value: Decimal
    day_min: Decimal | None  # the least amount for a day to count


def rule_of(challenge: Challenge) -> Rule:
    """The rule written in today's fields (`frequency`, `times`, `target_*`)."""
    f, t = Challenge.Frequency, Challenge.TargetScope
    total = challenge.target_value
    if challenge.target_scope == t.PER_WEEK and total:
        return Rule(WEEK, 0, AMOUNT, total, None)
    if challenge.target_scope == t.PER_PERIOD and total:
        return Rule(PERIOD, 0, AMOUNT, total, None)
    day_min = total if challenge.target_scope == t.PER_CHECK_IN and total else None
    times = Decimal(challenge.times or 0)
    if challenge.frequency == f.TIMES_PER_WEEK:
        return Rule(WEEK, 0, COUNT, times, day_min)
    if challenge.frequency == f.TIMES_PER_PERIOD:
        return Rule(PERIOD, 0, COUNT, times, day_min)
    if challenge.frequency == f.ONCE:
        return Rule(PERIOD, 0, COUNT, Decimal(1), day_min)
    on_days = challenge.weekdays if challenge.frequency == f.WEEKDAYS else 0
    return Rule(DAY, on_days, COUNT, Decimal(1), day_min)


@dataclass(frozen=True)
class Window:
    first: date
    last: date
    need: Decimal  # scaled down when the window is cut short
    full_need: Decimal


def counts_on(challenge: Challenge, day: date) -> bool:
    """Whether a check-in on `day` counts at all (chosen weekdays only, when there are some)."""
    mask = rule_of(challenge).on_days
    return not mask or bool(mask & (1 << day.weekday()))


def windows(challenge: Challenge, first: date, last: date) -> list[Window]:
    """The windows of the days `first`..`last` (one member's part), oldest first.

    A window that would ask for nothing after scaling is not judged, so it is left out.
    """
    rule = rule_of(challenge)
    result = []
    for start, end in _whole_windows(challenge, rule.window, first, last):
        kept_first, kept_last = max(start, first), min(end, last)
        kept = _counting_days(challenge, kept_first, kept_last)
        whole = _counting_days(challenge, start, end)
        if not kept:
            continue
        need = rule.need_value if kept == whole else _scaled(rule, kept, whole)
        if need > 0:
            result.append(Window(kept_first, kept_last, need, rule.need_value))
    return result


def window_at(challenge: Challenge, first: date, last: date, day: date) -> Window | None:
    """The window that `day` belongs to, if it is judged."""
    return next((w for w in windows(challenge, first, last) if w.first <= day <= w.last), None)


def _whole_windows(
    challenge: Challenge, kind: str, first: date, last: date
) -> list[tuple[date, date]]:
    """Every window touching `first`..`last`, before cutting it to those days."""
    if kind == PERIOD:
        assert challenge.period_start is not None
        assert challenge.end_date is not None
        return [(challenge.period_start, challenge.end_date)]
    if kind == WEEK:
        monday, _ = week_of(first)
        weeks = (last - monday).days // 7 + 1 if last >= monday else 0
        return [
            (monday + timedelta(weeks=n), monday + timedelta(weeks=n, days=6)) for n in range(weeks)
        ]
    return [(day, day) for day in _dates(first, last)]


def _counting_days(challenge: Challenge, first: date, last: date) -> int:
    return sum(1 for day in _dates(first, last) if counts_on(challenge, day))


def _dates(first: date, last: date) -> list[date]:
    return [first + timedelta(days=n) for n in range((last - first).days + 1)]


def _scaled(rule: Rule, kept: int, whole: int) -> Decimal:
    """The need in proportion to the days kept: whole check-ins, or amounts to one decimal."""
    step = Decimal(1) if rule.need_kind == COUNT else Decimal("0.1")
    return (rule.need_value * kept / whole).quantize(step, rounding=ROUND_HALF_UP)
