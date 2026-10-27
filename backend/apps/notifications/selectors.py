from datetime import datetime

from django.db.models import QuerySet

from apps.crews.models import Member

from .models import Notification

PAGE = 30


def mine(member: Member) -> QuerySet[Notification]:
    return Notification.objects.filter(recipient=member).select_related("actor")


def page(
    *, member: Member, before: datetime | None = None, limit: int = PAGE
) -> list[Notification]:
    """The member's news, latest first, up to `limit` rows older than `before` (the last row's
    `created_at` for the next page)."""
    rows = mine(member)
    if before is not None:
        rows = rows.filter(created_at__lt=before)
    return list(rows[:limit])


def unread_count(*, member: Member) -> int:
    return mine(member).filter(read_at__isnull=True).count()
