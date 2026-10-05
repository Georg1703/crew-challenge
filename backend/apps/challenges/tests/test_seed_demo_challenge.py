from io import StringIO

import pytest
import time_machine
from django.core.management import CommandError, call_command

from apps.challenges.models import Challenge, Participant

pytestmark = pytest.mark.django_db


def test_creates_a_challenge_running_this_month_once(settings):
    settings.DEBUG = True
    out = StringIO()
    with time_machine.travel("2026-11-10 12:00Z", tick=False):
        call_command("seed_demo", stdout=out)
        call_command("seed_demo_challenge", stdout=out)
        call_command("seed_demo_challenge", stdout=out)
    challenge = Challenge.objects.get(title="Plimbare (demo)")
    assert (str(challenge.start_date), str(challenge.end_date)) == ("2026-11-01", "2026-11-30")
    assert Participant.objects.filter(challenge=challenge).count() == 4
    assert "already runs" in out.getvalue()


def test_needs_debug_and_the_demo_crew(settings):
    settings.DEBUG = False
    with pytest.raises(CommandError, match="DEBUG"):
        call_command("seed_demo_challenge")
    settings.DEBUG = True
    with pytest.raises(CommandError, match="seed_demo"):
        call_command("seed_demo_challenge")
