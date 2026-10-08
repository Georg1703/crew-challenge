"""The crew's journal: check-ins, drawn spins and served ones, latest activity first.

Its own app because it is the one place that knows both kinds (check-ins must not import the
Wheel of Doom). Each kind pages its own rows after the cursor; the page is merged here, since
Django cannot filter a union.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from django.db.models import Q, QuerySet

from apps.checkins import selectors as checkins
from apps.crews.models import Member
from apps.doom import selectors as doom

CHECK_IN, SPIN, SERVED = "check_in", "spin", "served"
Cursor = tuple[datetime, UUID]  # the last item's activity_at and id


@dataclass
class Entry:
    kind: str
    activity_at: datetime
    item: Any  # a CheckIn from checkins.selectors.feed, a Spin from doom.selectors.journal/served


def _after(rows: QuerySet[Any], cursor: Cursor | None) -> QuerySet[Any]:
    if cursor is None:
        return rows
    at, pk = cursor
    return rows.filter(Q(activity_at__lt=at) | Q(activity_at=at, pk__lt=pk))


def page(*, member: Member, cursor: Cursor | None, size: int) -> tuple[list[Entry], Cursor | None]:
    """Up to `size` entries older than `cursor`, latest first, and the cursor of the next page
    (None at the end)."""
    found: list[Entry] = []
    for kind, rows in (
        (CHECK_IN, checkins.feed(member=member)),
        (SPIN, doom.journal(member=member)),
        (SERVED, doom.served(member=member)),
    ):
        newest = _after(rows, cursor).order_by("-activity_at", "-pk")[: size + 1]
        found += [Entry(kind, row.activity_at, row) for row in newest]
    found.sort(key=lambda entry: (entry.activity_at, entry.item.pk), reverse=True)
    entries = found[:size]
    more = len(found) > size
    return entries, ((entries[-1].activity_at, entries[-1].item.pk) if more else None)
