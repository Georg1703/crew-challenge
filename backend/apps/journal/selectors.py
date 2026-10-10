"""Reading the stored journal: a page of cards latest first, the cards one can react to, and the
day counts for a page's dividers."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from django.db.models import CharField, Count, IntegerField, Q, QuerySet, Sum
from django.db.models.fields.json import KeyTextTransform
from django.db.models.functions import Cast, Coalesce, Concat

from apps.challenges import selectors as challenges
from apps.crews.models import Member

from .models import JournalEntry

Cursor = tuple[datetime, UUID]  # the last card's `created_at` and id


def _visible(member: Member) -> QuerySet[JournalEntry]:
    """My crew's cards on challenges I can see, or on none (the crew's day)."""
    return JournalEntry.objects.filter(crew=member.crew).filter(
        Q(challenge__isnull=True) | Q(challenge__in=challenges.visible(member=member))
    )


def page(
    *, member: Member, cursor: Cursor | None, size: int
) -> tuple[list[JournalEntry], Cursor | None]:
    """Up to `size` cards I can see older than `cursor`, latest first. One query; cards never
    move, so walking the cursor never skips or repeats one. Also the cursor of the next page
    (None at the end)."""
    rows = _visible(member).select_related("member", "challenge").order_by("-created_at", "-id")
    if cursor is not None:
        at, pk = cursor
        rows = rows.filter(Q(created_at__lt=at) | Q(created_at=at, pk__lt=pk))
    found = list(rows[: size + 1])
    cards = found[:size]
    return cards, ((cards[-1].created_at, cards[-1].pk) if len(found) > size else None)


def reactable(member: Member, entry_id: UUID) -> JournalEntry | None:
    """A card I can see: reaction target `entry`."""
    return _visible(member).filter(pk=entry_id).first()


def day_counts(*, member: Member, days: set[date]) -> dict[date, tuple[int, int]]:
    """Per day, on what I can see: the check-ins (one per person and challenge, whatever their
    posts) and the photos and videos posted that day; for a journal page's dividers. One query."""
    if not days:
        return {}
    check_in = Q(kind=JournalEntry.Kind.CHECK_IN)
    who = Concat(Cast("member_id", CharField()), Cast("challenge_id", CharField()))
    files = Cast(KeyTextTransform("proofs", "facts"), IntegerField())
    rows = (
        _visible(member)
        .filter(day__in=days)
        .order_by()
        .values("day")
        .annotate(
            check_ins=Count(who, distinct=True, filter=check_in), proofs=Coalesce(Sum(files), 0)
        )
    )
    return {row["day"]: (row["check_ins"], row["proofs"]) for row in rows}
