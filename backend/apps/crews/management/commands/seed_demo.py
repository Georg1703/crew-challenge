"""Create demo crews with known logins for local development: `make seed`.

- Demo Crew: ana (admin), bogdan, cristina, dan.
- Eva's crew: eva (admin). Used to try joining a second crew with an existing account.

Safe to run more than once. Refuses to run when DEBUG is off, so it never touches production.
"""

from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.accounts import services as accounts
from apps.crews import services
from apps.crews.models import Crew

DEMO_PASSWORD = "garden-flame-2026"
DEMO_CREWS = [
    ("Demo Crew", [("ana", "Ana"), ("bogdan", "Bogdan"), ("cristina", "Cristina"), ("dan", "Dan")]),
    ("Echipa Eva", [("eva", "Eva")]),
]


class Command(BaseCommand):
    help = "Create the demo crews (known passwords). Local development only."

    def handle(self, *args: Any, **options: Any) -> None:
        if not settings.DEBUG:
            raise CommandError("seed_demo only runs with DEBUG on (local development).")
        for name, members in DEMO_CREWS:
            if Crew.objects.filter(name=name).exists():
                self.stdout.write(f"{name} already exists; nothing to do.")
                continue
            self._create(name, members)
            self.stdout.write(self.style.SUCCESS(f"Created {name}. Log in with:"))
            for index, (username, _) in enumerate(members):
                role = "admin" if index == 0 else "member"
                self.stdout.write(f"  {username:<10} {DEMO_PASSWORD}   ({role})")

    @staticmethod
    @transaction.atomic
    def _create(name: str, members: list[tuple[str, str]]) -> None:
        (admin_username, admin_name), *others = members
        admin_user = accounts.create_user(username=admin_username, password=DEMO_PASSWORD)
        admin = services.create_crew_with_admin(
            name=name, admin_user=admin_user, display_name=admin_name
        )
        for username, display_name in others:
            invite = services.create_invite(by=admin)
            services.accept_invite(
                code=invite.code,
                username=username,
                password=DEMO_PASSWORD,
                display_name=display_name,
            )
