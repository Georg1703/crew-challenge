from io import StringIO

import pytest
from django.core.management import CommandError, call_command

from apps.accounts.models import User
from apps.crews import selectors
from apps.crews.models import Crew, Member

pytestmark = pytest.mark.django_db


def test_seed_demo_creates_the_crew_once(settings):
    settings.DEBUG = True
    out = StringIO()
    call_command("seed_demo", stdout=out)
    call_command("seed_demo", stdout=out)

    crew = Crew.objects.get(name="Demo Crew")
    members = selectors.list_members(crew=crew)
    assert [m.user.username for m in members] == ["ana", "bogdan", "cristina", "dan"]
    assert members[0].is_admin
    assert "already exists" in out.getvalue()

    eva = selectors.list_members(crew=Crew.objects.get(name="Echipa Eva"))
    assert [(m.user.username, m.is_admin) for m in eva] == [("eva", True)]


def test_seed_demo_brings_back_demo_logins_that_were_removed(settings):
    settings.DEBUG = True
    call_command("seed_demo", stdout=StringIO())
    eva_crew = Crew.objects.get(name="Echipa Eva")
    User.objects.filter(username="eva").delete()  # her crew is left with nobody in it
    Member.objects.filter(user__username="dan").delete()  # his login stays

    out = StringIO()
    call_command("seed_demo", stdout=out)
    assert "Demo Crew: restored dan" in out.getvalue()
    assert "Echipa Eva: restored eva" in out.getvalue()
    eva = selectors.list_members(crew=eva_crew)
    assert [(m.user.username, m.is_admin) for m in eva] == [("eva", True)]
    assert Member.objects.filter(crew__name="Demo Crew", user__username="dan").exists()


def test_seed_demo_refuses_without_debug(settings):
    settings.DEBUG = False
    with pytest.raises(CommandError, match="DEBUG"):
        call_command("seed_demo")
    assert not Crew.objects.exists()
