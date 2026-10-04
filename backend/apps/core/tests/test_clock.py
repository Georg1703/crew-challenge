from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
import time_machine

from apps.core import clock

CHISINAU = "Europe/Chisinau"


@dataclass
class FakeCrew:
    timezone: str = CHISINAU


def test_now_is_aware_utc():
    current = clock.now()
    assert current.tzinfo is UTC


@time_machine.travel(datetime(2026, 11, 3, 12, 0, tzinfo=UTC), tick=False)
def test_now_and_utc_today_follow_frozen_time():
    assert clock.now() == datetime(2026, 11, 3, 12, 0, tzinfo=UTC)
    assert clock.utc_today() == date(2026, 11, 3)


@pytest.mark.parametrize(
    ("utc_instant", "expected_day"),
    [
        # Winter time (UTC+2) after 25 Oct 2026: local midnight is 22:00 UTC.
        (datetime(2026, 11, 3, 21, 59, 59, tzinfo=UTC), date(2026, 11, 3)),
        (datetime(2026, 11, 3, 22, 0, 0, tzinfo=UTC), date(2026, 11, 4)),
        # Summer time (UTC+3): local midnight is 21:00 UTC.
        (datetime(2026, 7, 10, 20, 59, 59, tzinfo=UTC), date(2026, 7, 10)),
        (datetime(2026, 7, 10, 21, 0, 0, tzinfo=UTC), date(2026, 7, 11)),
    ],
)
def test_crew_today_switches_at_local_midnight(utc_instant, expected_day):
    with time_machine.travel(utc_instant, tick=False):
        assert clock.crew_today(FakeCrew()) == expected_day
        assert clock.local_today(CHISINAU) == expected_day


def test_crew_today_differs_from_utc_date_late_in_the_evening():
    with time_machine.travel(datetime(2026, 10, 2, 22, 30, tzinfo=UTC), tick=False):
        assert clock.utc_today() == date(2026, 10, 2)
        assert clock.crew_today(FakeCrew()) == date(2026, 10, 3)


@pytest.mark.parametrize(
    ("day", "hours"),
    [
        (date(2026, 10, 25), 25),  # clocks go back: 04:00 -> 03:00
        (date(2026, 3, 29), 23),  # clocks go forward: 03:00 -> 04:00
        (date(2026, 11, 3), 24),
    ],
)
def test_day_bounds_follow_dst(day, hours):
    start, end = clock.day_bounds_utc(day, CHISINAU)
    assert end - start == timedelta(hours=hours)
    assert start.tzinfo is UTC
    assert end.tzinfo is UTC
    assert start.astimezone(ZoneInfo(CHISINAU)).hour == 0
    assert end.astimezone(ZoneInfo(CHISINAU)).date() == day + timedelta(days=1)


def test_deadline_on_dst_day_is_local_midnight_not_24_hours_later():
    start, _ = clock.day_bounds_utc(date(2026, 10, 25), CHISINAU)
    deadline = clock.deadline_utc(date(2026, 10, 25), CHISINAU)
    assert start == datetime(2026, 10, 24, 21, 0, tzinfo=UTC)  # 00:00 at UTC+3
    assert deadline == datetime(2026, 10, 25, 22, 0, tzinfo=UTC)  # 00:00 at UTC+2
    assert deadline - start != timedelta(hours=24)


def test_local_date_and_to_local():
    instant = datetime(2026, 11, 3, 23, 30, tzinfo=UTC)
    assert clock.local_date(instant, CHISINAU) == date(2026, 11, 4)
    assert clock.to_local(instant, CHISINAU).utcoffset() == timedelta(hours=2)


def test_naive_datetimes_are_rejected():
    with pytest.raises(ValueError, match="Naive datetime"):
        clock.to_local(datetime(2026, 11, 3, 12, 0), CHISINAU)


@pytest.mark.parametrize("name", ["Mars/Olympus", "", "../etc/passwd"])
def test_unknown_time_zone_is_rejected(name):
    with pytest.raises(clock.UnknownTimezone):
        clock.zone(name)
