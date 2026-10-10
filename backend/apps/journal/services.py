"""Writing the journal: the apps that make posts call `post` in the transaction that makes one, and
`drop` when a card's fact is gone. A card is never edited.

Synchronous on purpose: a card is a small indexed insert in a transaction the writer already has,
so it exists exactly when its post does (`docs/plans/journal.md`, "Sync or async").
"""

from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any

from django.contrib.contenttypes.models import ContentType
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models

from apps.challenges.models import Challenge
from apps.crews.models import Crew, Member

from .models import JournalEntry


def _key(kind: str, subject: models.Model, day: date) -> dict[str, Any]:
    return {
        "kind": kind,
        "subject_type": ContentType.objects.get_for_model(subject),
        "subject_id": subject.pk,
        "day": day,
    }


def _plain(facts: dict[str, Any]) -> dict[str, Any]:
    """Facts as JSON keeps them: decimals and dates as text."""
    plain: dict[str, Any] = json.loads(json.dumps(facts, cls=DjangoJSONEncoder))
    return plain


def post(
    kind: str,
    subject: models.Model,
    *,
    day: date,
    facts: dict[str, Any],
    member: Member | None,
    challenge: Challenge | None,
    at: datetime | None = None,
) -> JournalEntry:
    """Write `subject`'s `kind` card under `day` once. It is placed by `created_at`: now, or `at`
    for a post of the past (the backfill). Writing it again changes nothing: a card is never
    edited."""
    crew_id = subject.pk if isinstance(subject, Crew) else subject.crew_id  # type: ignore[attr-defined]
    entry, created = JournalEntry.objects.get_or_create(
        **_key(kind, subject, day),
        defaults={
            "crew_id": crew_id,
            "member": member,
            "challenge": challenge,
            "facts": _plain(facts),
        },
    )
    if created and at is not None and at != entry.created_at:
        entry.created_at = at  # the insert set it to now
        entry.save(update_fields=["created_at"])
    return entry


def drop(kind: str, subject: models.Model, *, day: date) -> None:
    """Delete `subject`'s `kind` card under `day`, if there is one."""
    JournalEntry.objects.filter(**_key(kind, subject, day)).delete()
