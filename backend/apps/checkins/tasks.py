"""Background jobs for check-ins. Missed days are not a job: they are derived on read (days.py)."""

from celery import shared_task

from . import services


@shared_task
def expire_proofs() -> int:
    """Every 15 minutes (config/celery.py): fail proof uploads that ran out of time."""
    return services.expire_proofs()
