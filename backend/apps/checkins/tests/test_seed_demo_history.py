from datetime import date
from io import StringIO

import pytest
import time_machine
from django.core.management import call_command

from apps.challenges.models import Challenge, Participant
from apps.challenges.windows import windows
from apps.checkins import days
from apps.checkins.models import CheckIn

pytestmark = pytest.mark.django_db


def test_builds_the_demo_history_once_and_meets_every_past_week(settings):
    settings.DEBUG = True
    out = StringIO()
    with time_machine.travel("2026-11-10 12:00Z", tick=False):
        call_command("seed_demo", stdout=out)
        call_command("seed_demo_history", stdout=out)
        call_command("seed_demo_history", stdout=out)
    assert "already there" in out.getvalue()
    assert Challenge.objects.filter(title__endswith="(demo)").count() == 4
    assert CheckIn.objects.exists()

    gym = Challenge.objects.get(window=Challenge.Window.WEEK)
    assert gym.start_date is not None
    today = date(2026, 11, 10)
    for p in Participant.objects.filter(challenge=gym):
        done = set(
            CheckIn.objects.filter(challenge=gym, member=p.member, status="done").values_list(
                "day", flat=True
            )
        )
        record = days.Record(done=done)
        closed = [w for w in windows(gym, gym.start_date, today) if w.last < today]
        assert closed
        assert all(days.judge(gym, w, record, today).state == "met" for w in closed)
