"""Drop the posters of finished videos that are (nearly) all one color, made before the app
picked the best of several frames: their phone's thumbnail shows instead. Safe to run twice.

    python manage.py repick_posters --dry-run
    python manage.py repick_posters
"""

from typing import Any

from django.core.management.base import BaseCommand, CommandParser

from apps.media import services


class Command(BaseCommand):
    help = "Drop black posters of finished videos so their phone thumbnail shows instead."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--dry-run", action="store_true", help="Only say what would change.")

    def handle(self, *args: Any, dry_run: bool = False, **options: Any) -> None:
        dropped = services.drop_blank_posters(dry_run=dry_run)
        verb = "Would drop" if dry_run else "Dropped"
        self.stdout.write(f"{verb} {len(dropped)} blank poster(s).")
        for key in dropped:
            self.stdout.write(f"  {key}")
