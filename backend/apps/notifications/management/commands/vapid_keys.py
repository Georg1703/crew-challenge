"""Make a VAPID key pair for Web Push, as the two lines the server's .env takes."""

from typing import Any

from django.core.management.base import BaseCommand

from integrations.push import make_vapid_keys


class Command(BaseCommand):
    help = "Print a fresh VAPID key pair as VAPID_PUBLIC_KEY and VAPID_PRIVATE_KEY lines."

    def handle(self, *args: Any, **options: Any) -> None:
        public, private = make_vapid_keys()
        self.stdout.write(f"VAPID_PUBLIC_KEY={public}\nVAPID_PRIVATE_KEY={private}")
