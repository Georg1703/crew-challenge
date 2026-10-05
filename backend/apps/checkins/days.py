"""Pure day rules: which days are due, how a day looks, streaks and progress.

No database and no clock here: callers pass crew-local dates (`clock.crew_today`) and the
check-ins they loaded. Nothing in this module assumes a month: a challenge runs from its
`start_date` to its `end_date`, and a participant until the day they left (`left_on`).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal

from apps.challenges.models import Challenge

FIXED = (Challenge.Frequency.DAILY, Challenge.Frequency.WEEKDAYS)


class DayState:
    DONE = "done"  # counted for the day
    PARTIAL = "partial"  # today: a number below the day's target
    TODO = "todo"  # today: due and not done yet
    OPEN = "open"  # today: not due, but a check-in counts toward the quota
    MISSED = "missed"  # a past due day without a check-in
    NOT_DUE = "not_due"  # nothing was asked that day
    FUTURE = "future"  # a day still to come
    OUTSIDE = "outside"  # before the participant started or after they stopped


@dataclass(frozen=True)
class Span:
    """The days one participant takes part in one challenge."""

    first: date
    last: date

    def __contains__(self, day: object) -> bool:
        return isinstance(day, date) and self.first <= day <= self.last

    def days(self, start: date, end: date) -> list[date]:
        lo, hi = max(start, self.first), min(end, self.last)
        return [lo + timedelta(days=n) for n in range((hi - lo).days + 1)] if lo <= hi else []


def span(challenge: Challenge, left_on: date | None) -> Span:
    """The days that count for one participant: the whole challenge, up to the day they left."""
    assert challenge.start_date is not None
    assert challenge.end_date is not None
    last = min(challenge.end_date, left_on) if left_on else challenge.end_date
    return Span(first=challenge.start_date, last=last)


@dataclass
class Record:
    """What a participant has: the days that counted and the totals per day."""

    done: set[date] = field(default_factory=set)
    partial: set[date] = field(default_factory=set)
    amounts: dict[date, Decimal] = field(default_factory=dict)


def is_fixed(challenge: Challenge) -> bool:
    """Daily and chosen-weekday challenges ask for specific days; the rest ask for a count."""
    return challenge.frequency in FIXED


def is_due(challenge: Challenge, day: date) -> bool:
    if challenge.frequency == Challenge.Frequency.DAILY:
        return True
    if challenge.frequency == Challenge.Frequency.WEEKDAYS:
        return bool(challenge.weekdays & (1 << day.weekday()))
    return False


def counts(challenge: Challenge, total: Decimal | None) -> bool:
    """Whether a day's check-in counts as done."""
    if challenge.measure != Challenge.Measure.QUANTITY:
        return True
    total = total or Decimal(0)
    if challenge.target_scope == Challenge.TargetScope.PER_CHECK_IN and challenge.target_value:
        return total >= challenge.target_value
    return total > 0


def state(challenge: Challenge, part: Span, record: Record, day: date, today: date) -> str:
    if day not in part:
        return DayState.OUTSIDE
    if day > today:
        return DayState.FUTURE
    if day in record.done:
        return DayState.DONE
    if day == today:
        if day in record.partial:
            return DayState.PARTIAL
        if is_fixed(challenge):
            return DayState.TODO if is_due(challenge, day) else DayState.NOT_DUE
        return DayState.OPEN
    if is_fixed(challenge) and is_due(challenge, day):
        return DayState.MISSED
    return DayState.NOT_DUE


def week_of(day: date) -> tuple[date, date]:
    monday = day - timedelta(days=day.weekday())
    return monday, monday + timedelta(days=6)


def week_quota(challenge: Challenge, part: Span, day: date) -> int:
    """Times asked in the week of `day`: a partial first or last week asks for fewer."""
    monday, sunday = week_of(day)
    return min(challenge.times or 0, len(part.days(monday, sunday)))


def done_between(record: Record, part: Span, start: date, end: date) -> int:
    return sum(1 for d in part.days(start, end) if d in record.done)


def streak(challenge: Challenge, part: Span, record: Record, today: date) -> int | None:
    """Due days (daily, weekdays) or weeks (times a week) in a row without a miss.

    Today, or this week, only adds to the streak once it is done: it is never a break.
    Challenges asked a number of times per period, or once, have progress instead (None).
    """
    if is_fixed(challenge):
        count, day = 0, min(today, part.last)
        if day == today and day in record.done:
            count, day = 1, day - timedelta(days=1)
        elif day == today:
            day -= timedelta(days=1)
        while day >= part.first:
            if is_due(challenge, day):
                if day not in record.done:
                    break
                count += 1
            day -= timedelta(days=1)
        return count
    if challenge.frequency == Challenge.Frequency.TIMES_PER_WEEK:
        count, (monday, sunday) = 0, week_of(min(today, part.last))
        current = True
        while sunday >= part.first:
            quota = week_quota(challenge, part, monday)
            met = done_between(record, part, monday, sunday) >= quota > 0
            if met:
                count += 1
            elif not current:
                break
            current = False
            monday, sunday = monday - timedelta(days=7), sunday - timedelta(days=7)
        return count
    return None


@dataclass(frozen=True)
class Progress:
    """Toward a count of days (`days`) or a total (`amount`)."""

    kind: str
    done: Decimal
    goal: Decimal


def progress(challenge: Challenge, part: Span, record: Record, today: date) -> Progress | None:
    """Progress toward the week's or the period's goal; None for daily and weekday challenges
    without a weekly or period target."""
    monday, sunday = week_of(today)
    if challenge.measure == Challenge.Measure.QUANTITY and challenge.target_value:
        if challenge.target_scope == Challenge.TargetScope.PER_WEEK:
            total = sum(
                (record.amounts.get(d, Decimal(0)) for d in part.days(monday, sunday)), Decimal(0)
            )
            return Progress("amount", total, challenge.target_value)
        if challenge.target_scope == Challenge.TargetScope.PER_PERIOD:
            total = sum(
                (record.amounts.get(d, Decimal(0)) for d in part.days(part.first, today)),
                Decimal(0),
            )
            return Progress("amount", total, challenge.target_value)
    if challenge.frequency == Challenge.Frequency.TIMES_PER_WEEK:
        return Progress(
            "days",
            Decimal(done_between(record, part, monday, sunday)),
            Decimal(week_quota(challenge, part, today)),
        )
    if challenge.frequency == Challenge.Frequency.TIMES_PER_PERIOD:
        return Progress(
            "days",
            Decimal(done_between(record, part, part.first, today)),
            Decimal(challenge.times or 0),
        )
    if challenge.frequency == Challenge.Frequency.ONCE:
        return Progress(
            "days", Decimal(min(1, done_between(record, part, part.first, today))), Decimal(1)
        )
    return None


def settled_today(challenge: Challenge, part: Span, record: Record, today: date) -> bool | None:
    """Whether today's ring segment for this challenge is full; None if it has no segment.

    Fixed challenges have a segment on due days, full once today is done. Flexible ones always
    have one, full once checked in today or once the week's or period's count is reached.
    """
    if today not in part:
        return None
    if is_fixed(challenge):
        return today in record.done if is_due(challenge, today) else None
    if today in record.done:
        return True
    goal = progress(challenge, part, record, today)
    return goal is not None and goal.kind == "days" and goal.done >= goal.goal > 0
