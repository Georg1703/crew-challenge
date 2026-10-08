from django.apps import AppConfig


class DoomConfig(AppConfig):
    name = "apps.doom"
    label = "doom"
    verbose_name = "Wheel of Doom"

    def ready(self) -> None:
        from apps.reactions.targets import Target, register

        from . import selectors
        from .models import Spin

        register(Target(key="spin", model=Spin, find=selectors.reactable_spin))
