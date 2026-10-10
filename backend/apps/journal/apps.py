from django.apps import AppConfig


class JournalConfig(AppConfig):
    name = "apps.journal"
    label = "journal"
    verbose_name = "Journal"

    def ready(self) -> None:
        from apps.crews.targets import Target, register

        from . import selectors
        from .models import JournalEntry

        register(Target(key="entry", model=JournalEntry, visible=selectors.visible, comments=True))
