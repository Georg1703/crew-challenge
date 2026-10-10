"""Write the stored journal's cards of everything posted so far, with the same writers the app
uses: every check-in post, every finished crew day, every drawn and served spin. Safe to run
twice (a card is written once); the repair tool if a writer ever leaves a gap.
"""

from typing import Any

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Max

from apps.checkins import services as checkins
from apps.checkins.models import CheckInEntry
from apps.crews.models import Crew
from apps.doom import services as doom
from apps.doom.models import Spin
from apps.journal.models import JournalEntry


class Command(BaseCommand):
    help = "Write the journal's cards of everything posted so far. Safe to run twice."

    @transaction.atomic
    def handle(self, *args: Any, **options: Any) -> None:
        entries = CheckInEntry.objects.select_related(
            "check_in__challenge__crew", "check_in__member", "check_in__crew"
        ).order_by("check_in__day", "created_at")
        for entry in entries:
            checkins.write_card(entry)
        days = (
            CheckInEntry.objects.order_by()
            .values("crew_id", "check_in__day")
            .annotate(last=Max("created_at"))  # about when the day was finished
        )
        crews = {crew.pk: crew for crew in Crew.objects.filter(pk__in={d["crew_id"] for d in days})}
        for found in days:
            checkins.write_crew_day(
                crew=crews[found["crew_id"]], day=found["check_in__day"], at=found["last"]
            )
        spins = Spin.objects.filter(drawn_at__isnull=False).select_related(
            "challenge__crew", "member", "punishment"
        )
        for spin in spins:
            doom.write_cards(spin)
        self.stdout.write(f"Journal cards: {JournalEntry.objects.count()}")
