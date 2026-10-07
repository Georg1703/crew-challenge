"""Pure day rules: how a day looks, how a window is judged, streaks and progress.

No database and no clock here: callers pass crew-local dates (`clock.crew_today`) and the
check-ins they loaded. Which windows a challenge has and what each one needs comes from
`apps.challenges.windows`; this module judges them against what a participant did.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal

from apps.challenges import windows
from apps.challenges.models import Challenge
from apps.challenges.windows import Window


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
    """What a participant has: the days that counted, the totals per day, days with proof."""

    done: set[date] = field(default_factory=set)
    partial: set[date] = field(default_factory=set)
    amounts: dict[date, Decimal] = field(default_factory=dict)
    proof_days: set[date] = field(default_factory=set)


def is_fixed(challenge: Challenge) -> bool:
    """Judged day by day (every day, or chosen days); the rest are judged over longer windows."""
    return challenge.window == Challenge.Window.DAY


def is_due(challenge: Challenge, day: date) -> bool:
    """A day a challenge judged day by day asks for."""
    return is_fixed(challenge) and windows.counts_on(challenge, day)


def counts(challenge: Challenge, total: Decimal | None) -> bool:
    """Whether a day's check-in counts as done."""
    if challenge.measure != Challenge.Measure.QUANTITY:
        return True
    total = total or Decimal(0)
    return total >= challenge.day_min if challenge.day_min else total > 0


@dataclass(frozen=True)
class Verdict:
    """How a window stands on a given day."""

    MET = "met"  # reached its need (it can be met before it ends)
    FAILED = "failed"  # ended below its need
    OPEN = "open"  # today is in it and its need isn't reached yet
    FUTURE = "future"  # starts after today

    state: str
    done: Decimal
    need: Decimal

    @property
    def short(self) -> Decimal:
        """How much a failed window lacked."""
        return self.need - self.done if self.state == self.FAILED else Decimal(0)


def judge(challenge: Challenge, window: Window, record: Record, today: date) -> Verdict:
    """The verdict on one window, from the days up to today that count."""
    if window.first > today:
        return Verdict(Verdict.FUTURE, Decimal(0), window.need)
    seen = [
        d
        for d in Span(window.first, window.last).days(window.first, today)
        if windows.counts_on(challenge, d)
    ]
    if challenge.need_kind == Challenge.NeedKind.AMOUNT:
        done = sum((record.amounts.get(d, Decimal(0)) for d in seen), Decimal(0))
    else:
        done = Decimal(sum(1 for d in seen if d in record.done))
    if done >= window.need:
        return Verdict(Verdict.MET, done, window.need)
    if window.last >= today:
        return Verdict(Verdict.OPEN, done, window.need)
    return Verdict(Verdict.FAILED, done, window.need)


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
        if not windows.counts_on(challenge, day):
            return DayState.NOT_DUE
        return DayState.TODO if is_fixed(challenge) else DayState.OPEN
    return DayState.MISSED if is_due(challenge, day) else DayState.NOT_DUE


def _verdicts(challenge: Challenge, part: Span, record: Record, today: date) -> list[str]:
    return [
        judge(challenge, w, record, today).state
        for w in windows.windows(challenge, part.first, part.last)
    ]


def streak(challenge: Challenge, part: Span, record: Record, today: date) -> int | None:
    """Windows in a row that were met, counting back from the newest: due days or weeks.

    The window still open today is skipped, so it never breaks the streak. A challenge judged
    once over its whole period has progress instead (None).
    """
    if challenge.window == Challenge.Window.PERIOD:
        return None
    count = 0
    for verdict in reversed(_verdicts(challenge, part, record, today)):
        if verdict == Verdict.MET:
            count += 1
        elif verdict == Verdict.FAILED:
            break
    return count


def longest_streak(challenge: Challenge, part: Span, record: Record, today: date) -> int | None:
    """The longest run so far of met windows in a row. None when judged over the whole period."""
    if challenge.window == Challenge.Window.PERIOD:
        return None
    best = run = 0
    for verdict in _verdicts(challenge, part, record, today):
        if verdict == Verdict.MET:
            run += 1
            best = max(best, run)
        elif verdict == Verdict.FAILED:
            run = 0
    return best


@dataclass(frozen=True)
class Progress:
    """Toward a count of days (`days`) or a total (`amount`)."""

    kind: str
    done: Decimal
    goal: Decimal


def progress(challenge: Challenge, part: Span, record: Record, today: date) -> Progress | None:
    """Progress in today's window (a week or the whole period); None when judged day by day."""
    if is_fixed(challenge):
        return None
    window = windows.window_at(challenge, part.first, part.last, today)
    if window is None:
        return None
    verdict = judge(challenge, window, record, today)
    kind = "amount" if challenge.need_kind == Challenge.NeedKind.AMOUNT else "days"
    return Progress(kind, verdict.done, window.need)


def settled_today(challenge: Challenge, part: Span, record: Record, today: date) -> bool | None:
    """Whether today's ring segment for this challenge is full; None if it has no segment.

    Challenges judged day by day have a segment on due days, full once today is done. The others
    have one on every day that counts, full once checked in today or once the window's count is
    reached.
    """
    if today not in part or not windows.counts_on(challenge, today):
        return None
    if is_fixed(challenge):
        return today in record.done
    if today in record.done:
        return True
    goal = progress(challenge, part, record, today)
    return goal is not None and goal.kind == "days" and goal.done >= goal.goal > 0
