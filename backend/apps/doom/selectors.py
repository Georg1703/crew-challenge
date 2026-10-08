"""Wheel of Doom reads: my open spins, and drawn spins for the crew's journal."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from django.contrib.contenttypes.models import ContentType
from django.db.models import Exists, OuterRef, Q, QuerySet, Subquery
from django.db.models.functions import Greatest

from apps.challenges import selectors as challenges
from apps.core import clock
from apps.crews.models import Member
from apps.proofs.models import Proof
from apps.proofs.selectors import SHOWN

from .models import Spin

PENDING, SPUN, SERVED = "pending", "spun", "served"


def _shown_proofs() -> QuerySet[Proof]:
    """Shown proofs of the spin in the outer query."""
    return Proof.objects.filter(
        subject_type=ContentType.objects.get_for_model(Spin),
        subject_id=OuterRef("pk"),
        status__in=SHOWN,
    )


def _with_state(rows: QuerySet[Spin]) -> QuerySet[Spin]:
    return rows.annotate(has_shown=Exists(_shown_proofs())).select_related(
        "challenge", "member", "punishment"
    )


def state(spin: Spin) -> str:
    """`pending` (not drawn), `spun` (drawn, not served) or `served`, on a spin from these reads."""
    if spin.punishment_id is None:
        return PENDING
    return SERVED if spin.done_at or spin.has_shown else SPUN  # type: ignore[attr-defined]


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
    """My spins (on challenges I left too), with my proofs on them, every status."""
    return (
        _with_state(Spin.objects.for_crew(member.crew).filter(member=member))
        .select_related("challenge__crew")
        .prefetch_related("proofs__original__transcode", "proofs__thumb")
    )


def mine(*, member: Member, spin_id: UUID) -> Spin | None:
    return _mine(member).filter(pk=spin_id).first()


def owed(*, member: Member) -> Owed:
    """My spins not served yet, oldest window first (the Today card and the spins page)."""
    rows = list(
        _mine(member)
        .filter(Q(punishment__isnull=True) | Q(done_at__isnull=True, has_shown=False))
        .order_by("window_first", "challenge__title", "number")
    )
    to_spin = sum(1 for spin in rows if spin.punishment_id is None)
    return Owed(spins=rows, to_spin=to_spin, to_serve=len(rows) - to_spin)


def journal(*, member: Member) -> QuerySet[Spin]:
    """Drawn spins on challenges the member can see, with `activity_at`: the later of the draw,
    "Done" and the newest shown proof (`Greatest` skips what is empty)."""
    newest_proof = _shown_proofs().order_by("-updated_at").values("updated_at")[:1]
    return (
        _with_state(Spin.objects.filter(challenge__in=challenges.visible(member=member)))
        .filter(drawn_at__isnull=False)
        .annotate(activity_at=Greatest("drawn_at", "done_at", Subquery(newest_proof)))
        .select_related("challenge__crew")
    )


def reactable_spin(member: Member, spin_id: UUID) -> Spin | None:
    """A drawn spin the member sees in the journal (reaction target `spin`)."""
    return journal(member=member).filter(pk=spin_id).first()


def shown_proofs(spins: list[Spin]) -> dict[UUID, list[Proof]]:
    """Each spin's proofs the crew can see, for a journal page, in one query."""
    result: dict[UUID, list[Proof]] = {spin.pk: [] for spin in spins}
    rows = (
        Proof.objects.filter(spin__in=spins, status__in=SHOWN)
        .select_related("original__transcode", "thumb")
        .order_by("created_at")
    )
    for proof in rows:
        result[proof.subject_id].append(proof)
    return result
