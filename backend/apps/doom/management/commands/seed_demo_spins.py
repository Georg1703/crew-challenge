"""Give Demo Crew spins to try the Wheel of Doom, locally and in e2e: `make seed`.

"Roata (demo)": three times a week, two weeks from last week's Monday, the whole Demo Crew, two
punishments that need no proof. Nobody checked in last week, so everyone owes three spins. Each
run starts over (last week's dates again, its spins opened afresh, drawn ones too), so an e2e test
can spin again. Writes rows directly, like seed_demo_challenge, and only with DEBUG.
"""

from datetime import timedelta
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.challenges.models import Challenge, Participant, Punishment
from apps.core import clock
from apps.crews import selectors as crews
from apps.crews.models import Crew
from apps.doom import services
from apps.doom.models import Spin

TITLE = "Roata (demo)"
PUNISHMENTS = ["F\u0103r\u0103 telefon dup\u0103 21:00", "Speli vasele disear\u0103"]


class Command(BaseCommand):
    help = "Give Demo Crew a challenge whose last week owes spins. Local development only."

    @transaction.atomic
    def handle(self, *args: Any, **options: Any) -> None:
        if not settings.DEBUG:
            raise CommandError("seed_demo_spins only runs with DEBUG on (local development).")
        crew = Crew.objects.filter(name="Demo Crew").first()
        if crew is None:
            raise CommandError("Run seed_demo first: Demo Crew does not exist.")
        today = clock.crew_today(crew)
        monday = today - timedelta(days=today.weekday() + 7)  # last week's
        dates = {"period_start": monday, "start_date": monday, "end_date": monday + timedelta(13)}
        members = crews.list_members(crew=crew)
        admin = next(m for m in members if m.is_admin)
        challenge = Challenge.objects.for_crew(crew).filter(title=TITLE).first()
        if challenge is None:
            challenge = Challenge.objects.create(
                crew=crew,
                created_by=admin,
                title=TITLE,
                icon="star",
                window=Challenge.Window.WEEK,
                need_value=3,
                state=Challenge.State.CHOSEN,
                period_kind="week",
                period_length=2,
                chosen_by=admin,
                chosen_at=clock.now(),
                **dates,
            )
            Punishment.objects.bulk_create(
                Punishment(crew=crew, challenge=challenge, position=n, text=text)
                for n, text in enumerate(PUNISHMENTS, start=1)
            )
        else:
            Challenge.objects.filter(pk=challenge.pk).update(**dates)
            Spin.objects.filter(challenge=challenge).delete()
        for member in members:
            Participant.objects.get_or_create(crew=crew, challenge=challenge, member=member)
        opened = services.open_spins()
        self.stdout.write(f"{TITLE}: {opened} spins opened from the week of {monday}.")
