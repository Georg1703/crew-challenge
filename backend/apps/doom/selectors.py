"""Wheel of Doom reads: my spins, open ones first (their cards are in the journal)."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from django.db.models import QuerySet

from apps.core import clock
from apps.crews.models import Member

from .models import Spin

PENDING, SPUN, SERVED = "pending", "spun", "served"


def state(spin: Spin) -> str:
    """`pending` (not drawn), `spun` (drawn, not served) or `served`."""
    if spin.punishment_id is None:
        return PENDING
    return SERVED if spin.done_at else SPUN


def late(spin: Spin) -> bool:
    return (
        state(spin) == SPUN
        and spin.serve_by is not None
        and clock.crew_today(spin.challenge.crew) > spin.serve_by
    )


@dataclass
class Owed:
    spins: list[Spin]  # oldest first
    to_spin: int
    to_serve: int


def _mine(member: Member) -> QuerySet[Spin]:
    """My spins (on challenges I left too), with my proofs on them: posted and draft, every
    status."""
    return (
        Spin.objects.for_crew(member.crew)
        .filter(member=member)
        .select_related("challenge__crew", "member", "punishment")
        .prefetch_related("proofs__original__transcode", "proofs__thumb")
    )


def mine(*, member: Member, spin_id: UUID) -> Spin | None:
    return _mine(member).filter(pk=spin_id).first()


def owed(*, member: Member) -> Owed:
    """My spins not served yet, oldest window first (the Today card and the spins page)."""
    rows = list(
        _mine(member)
        .filter(done_at__isnull=True)
        .order_by("window_first", "challenge__title", "number")
    )
    to_spin = sum(1 for spin in rows if spin.punishment_id is None)
    return Owed(spins=rows, to_spin=to_spin, to_serve=len(rows) - to_spin)
