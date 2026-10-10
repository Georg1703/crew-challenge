"""Reading the stored journal: a page of cards, latest first."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from django.db.models import Q

from apps.challenges import selectors as challenges
from apps.crews.models import Member

from .models import JournalEntry

Cursor = tuple[datetime, UUID]  # the last card's `created_at` and id


def page(
    *, member: Member, cursor: Cursor | None, size: int
) -> tuple[list[JournalEntry], Cursor | None]:
    """Up to `size` cards of my crew older than `cursor`, latest first: on challenges I can see, or
    on none (the crew's day). One query; cards never move, so walking the cursor never skips or
    repeats one. Also the cursor of the next page (None at the end)."""
    rows = (
        JournalEntry.objects.filter(crew=member.crew)
        .filter(Q(challenge__isnull=True) | Q(challenge__in=challenges.visible(member=member)))
        .select_related("member", "challenge")
        .order_by("-created_at", "-id")
    )
    if cursor is not None:
        at, pk = cursor
        rows = rows.filter(Q(created_at__lt=at) | Q(created_at=at, pk__lt=pk))
    found = list(rows[: size + 1])
    cards = found[:size]
    return cards, ((cards[-1].created_at, cards[-1].pk) if len(found) > size else None)
