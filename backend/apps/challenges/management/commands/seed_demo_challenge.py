"""Give the demo crew a challenge that runs today, for trying check-ins locally: `make seed`.

"Plimbare (demo)": every day of the current month, the whole Demo Crew takes part. Scheduling
through the app can only start a challenge tomorrow, so this writes the rows directly. Safe to run
more than once (one per month). Refuses to run when DEBUG is off, so it never touches production.
"""

from datetime import timedelta
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.challenges import periods
from apps.challenges.models import Challenge, Participant
from apps.core import clock
from apps.crews import selectors as crews
from apps.crews.models import Crew

TITLE = "Plimbare (demo)"


class Command(BaseCommand):
    help = "Create a demo challenge running this month in Demo Crew. Local development only."

    @transaction.atomic
    def handle(self, *args: Any, **options: Any) -> None:
        if not settings.DEBUG:
            raise CommandError("seed_demo_challenge only runs with DEBUG on (local development).")
        crew = Crew.objects.filter(name="Demo Crew").first()
        if crew is None:
            raise CommandError("Run seed_demo first: Demo Crew does not exist.")
        first, last = periods.month_of(clock.crew_today(crew))
        if Challenge.objects.for_crew(crew).filter(title=TITLE, start_date=first).exists():
            self.stdout.write(f"{TITLE} already runs this month; nothing to do.")
            return
        members = crews.list_members(crew=crew)
        admin = next(m for m in members if m.is_admin)
        challenge = Challenge.objects.create(
            crew=crew,
            created_by=admin,
            title=TITLE,
            icon="walk",
            frequency=Challenge.Frequency.DAILY,
            state=Challenge.State.CHOSEN,
            period_kind="month",
            period_start=first,
            start_date=first,
            end_date=last,
            chosen_by=admin,
            chosen_at=clock.now() - timedelta(days=1),
        )
        for member in members:
            Participant.objects.create(crew=crew, challenge=challenge, member=member)
        self.stdout.write(self.style.SUCCESS(f"Created {TITLE} ({first} - {last})."))
