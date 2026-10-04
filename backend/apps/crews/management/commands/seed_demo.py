"""Create a demo crew with known logins for local development: `make seed`.

Safe to run more than once. Refuses to run when DEBUG is off, so it never touches production.
"""

from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.accounts import services as accounts
from apps.crews import services
from apps.crews.models import Crew

DEMO_CREW = "Demo Crew"
DEMO_PASSWORD = "garden-flame-2026"
DEMO_MEMBERS = [("ana", "Ana"), ("bogdan", "Bogdan"), ("cristina", "Cristina"), ("dan", "Dan")]


class Command(BaseCommand):
    help = "Create the demo crew (4 members, known passwords). Local development only."

    def handle(self, *args: Any, **options: Any) -> None:
        if not settings.DEBUG:
            raise CommandError("seed_demo only runs with DEBUG on (local development).")
        if Crew.objects.filter(name=DEMO_CREW).exists():
            self.stdout.write(f"{DEMO_CREW} already exists; nothing to do.")
            return
        with transaction.atomic():
            (admin_username, admin_name), *others = DEMO_MEMBERS
            admin_user = accounts.create_user(username=admin_username, password=DEMO_PASSWORD)
            admin = services.create_crew_with_admin(
                name=DEMO_CREW, admin_user=admin_user, display_name=admin_name
            )
            for username, name in others:
                invite = services.create_invite(by=admin)
                services.accept_invite(
                    code=invite.code, username=username, password=DEMO_PASSWORD, display_name=name
                )
        self.stdout.write(self.style.SUCCESS(f"Created {DEMO_CREW}. Log in with:"))
        for username, _ in DEMO_MEMBERS:
            role = "admin" if username == admin_username else "member"
            self.stdout.write(f"  {username:<10} {DEMO_PASSWORD}   ({role})")
