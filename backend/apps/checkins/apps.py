from django.apps import AppConfig


class CheckinsConfig(AppConfig):
    name = "apps.checkins"
    label = "checkins"
    verbose_name = "Check-ins"

    def ready(self) -> None:
        from apps.reactions.targets import Target, register

        from . import selectors
        from .models import CheckIn

        register(Target(key="check_in", model=CheckIn, find=selectors.reactable_check_in))
