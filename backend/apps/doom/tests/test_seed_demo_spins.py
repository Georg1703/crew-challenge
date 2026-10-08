from io import StringIO

import pytest
import time_machine
from django.core.management import call_command

from apps.doom import services
from apps.doom.models import Spin

pytestmark = pytest.mark.django_db


def test_the_demo_crew_owes_three_spins_each_and_a_new_run_starts_over(settings):
    settings.DEBUG = True
    out = StringIO()
    with time_machine.travel("2026-11-11 10:00Z", tick=False):  # a Wednesday
        call_command("seed_demo", stdout=out)
        call_command("seed_demo_spins", stdout=out)
        spins = Spin.objects.all()
        assert {s.window_first.isoformat() for s in spins} == {"2026-11-02"}  # last week
        per_member = {
            m: spins.filter(member=m).count() for m in spins.values_list("member", flat=True)
        }
        assert set(per_member.values()) == {3}
        first = spins.first()
        assert first is not None
        services.draw(by=first.member, spin_id=first.pk)
        call_command("seed_demo_spins", stdout=out)
    assert not Spin.objects.filter(punishment__isnull=False).exists()  # drawn ones start over
    assert "spins opened" in out.getvalue()
