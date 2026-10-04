"""The only source of "current time" for business logic.

Rules (enforced by ruff's banned-api check outside this module):
- Instants are timezone-aware datetimes in UTC. Never create or store naive datetimes.
- A crew's "day" is a calendar date in the crew's IANA time zone (for example Europe/Chisinau).
  Store it as a date, not as a datetime at midnight.
- Never compute day boundaries as "now - 24 hours": a day can be 23 or 25 hours long when daylight
  saving time changes. Use day_bounds_utc() instead.

Tests freeze time with time_machine; everything here follows it.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from functools import lru_cache
from typing import Protocol
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


class HasTimezone(Protocol):
    """Anything with an IANA time zone name, for example a Crew."""

    @property
    def timezone(self) -> str: ...


class UnknownTimezone(ValueError):
    """Raised for a time zone name that is not in the IANA database."""


@lru_cache(maxsize=64)
def zone(name: str) -> ZoneInfo:
    """Return the ZoneInfo for an IANA name such as "Europe/Chisinau"."""
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise UnknownTimezone(f"Unknown time zone: {name!r}") from exc


def now() -> datetime:
    """The current instant, timezone-aware, in UTC."""
    return datetime.now(UTC)


def utc_today() -> date:
    """Today's date in UTC. Use only for technical things (logs, file paths), not game days."""
    return now().date()


def local_today(tz_name: str) -> date:
    """Today's calendar date in the given time zone."""
    return now().astimezone(zone(tz_name)).date()


def crew_today(crew: HasTimezone) -> date:
    """Today's challenge day for a crew."""
    return local_today(crew.timezone)


def to_local(instant: datetime, tz_name: str) -> datetime:
    """Convert an aware instant to local time in the given zone."""
    _require_aware(instant)
    return instant.astimezone(zone(tz_name))


def local_date(instant: datetime, tz_name: str) -> date:
    """The calendar date an aware instant falls on in the given zone."""
    return to_local(instant, tz_name).date()


def day_bounds_utc(day: date, tz_name: str) -> tuple[datetime, datetime]:
    """UTC start (inclusive) and end (exclusive) of a local calendar day.

    The end is the day's deadline: local midnight that starts the next day. On DST change days
    the span is 23 or 25 hours.
    """
    tz = zone(tz_name)
    start = datetime.combine(day, time.min, tzinfo=tz).astimezone(UTC)
    end = datetime.combine(day + timedelta(days=1), time.min, tzinfo=tz).astimezone(UTC)
    return start, end


def deadline_utc(day: date, tz_name: str) -> datetime:
    """The UTC instant at which a local challenge day ends."""
    return day_bounds_utc(day, tz_name)[1]


def _require_aware(instant: datetime) -> None:
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise ValueError("Naive datetime: every instant must be timezone-aware (UTC).")
