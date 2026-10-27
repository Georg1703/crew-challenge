"""Background jobs for notifications."""

from uuid import UUID

from celery import shared_task

from . import services


@shared_task
def push(notification_id: str) -> int:
    """After a notification is posted: send it to the recipient's devices."""
    return services.send_push(notification_id=UUID(notification_id))


@shared_task
def prune_notifications() -> int:
    """Nightly (config/celery.py): drop news older than 90 days."""
    return services.prune()
