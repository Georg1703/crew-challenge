"""Background jobs for the Wheel of Doom."""

from celery import shared_task

from . import services


@shared_task
def open_spins() -> int:
    """Every 15 minutes (config/celery.py): open the spins owed for windows that closed."""
    return services.open_spins()
