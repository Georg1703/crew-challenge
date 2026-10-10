"""Wheel of Doom rules: open the spins owed, draw them on the server, serve them.

A window that ended below its need owes one spin per missing check-in, or one for a missed total,
on a challenge with punishments (the others never spin). Spins are opened by a job, never on
read, and once only (a unique key per window and number). Drawing happens before the dial turns;
a drawn punishment is served by a shown proof or, when it needs none, by "Done", by `serve_by`
(after that it is late, nothing more in v1).
"""

from __future__ import annotations

import math
import random
import secrets
from datetime import timedelta
from uuid import UUID

from django.db import transaction

from apps.challenges import selectors as challenges
from apps.challenges.models import Challenge
from apps.checkins import days
from apps.checkins import selectors as checkins
from apps.core import clock
from apps.core.errors import Conflict, NotFound
from apps.crews.models import Member
from apps.proofs import services as proofs

from .models import Spin

SERVE_DAYS = 7
UPLOAD_TIME = timedelta(hours=24)  # a spin's proof must finish uploading within this


class SpinNotFound(NotFound):
    code = "spin_not_found"
    message = "This spin does not exist."


class NotDrawn(Conflict):
    code = "not_drawn"
    message = "Spin the wheel first."


class ProofNeeded(Conflict):
    code = "proof_needed"
    message = "This punishment is served with a photo or a video."


class ProofNotNeeded(Conflict):
    code = "proof_not_needed"
    message = 'This punishment needs no proof: tap "Done".'


def owed(challenge: Challenge, verdict: days.Verdict) -> int:
    """Spins a failed window owes: one per missing check-in, or one for a missed total."""
    if challenge.need_kind == Challenge.NeedKind.AMOUNT:
        return 1
    return max(1, math.ceil(verdict.short))


def open_spins() -> int:
    """Open every spin owed for windows that closed; returns how many are new. Safe to run twice.

    Looks at every scheduled challenge with punishments and every participant, those who left too
    (their cut window counts).
    """
    # ponytail: judges every closed window each run; a "judged until" mark per participant if
    # crews ever grow past a few hundred windows.
    found = list(
        Challenge.objects.filter(state=Challenge.State.CHOSEN, punishments__isnull=False)
        .distinct()
        .select_related("crew")
    )
    people = challenges.participants(challenges=found)
    before = Spin.objects.count()
    rows: list[Spin] = []
    for challenge in found:
        today = clock.crew_today(challenge.crew)
        taking_part = people.get(challenge.pk, [])
        loaded = checkins.records(
            challenge_ids=[challenge.pk],
            member_ids=[p.member_id for p in taking_part],
            proof_days=False,
        )
        for participant in taking_part:
            part = days.span(challenge, participant.left_on)
            record = loaded.get((challenge.pk, participant.member_id), days.Record())
            for judged in days.judged(challenge, part, record, today):
                verdict = judged.verdict
                if verdict is None or verdict.state != days.Verdict.FAILED:
                    continue
                rows += [
                    Spin(
                        crew_id=challenge.crew_id,
                        challenge=challenge,
                        member_id=participant.member_id,
                        window_first=judged.window.first,
                        window_last=judged.window.last,
                        number=number,
                        need=verdict.need,
                        done=verdict.done,
                    )
                    for number in range(1, owed(challenge, verdict) + 1)
                ]
    Spin.objects.bulk_create(rows, ignore_conflicts=True)
    return Spin.objects.count() - before


def _own(by: Member, spin_id: UUID) -> Spin:
    """My spin, locked for the change that follows."""
    spin = (
        Spin.objects.select_for_update(of=("self",))
        .filter(pk=spin_id, member=by)
        .select_related("punishment")
        .first()
    )
    if spin is None:
        raise SpinNotFound()
    return spin


@transaction.atomic
def draw(*, by: Member, spin_id: UUID, rng: random.Random | None = None) -> Spin:
    """Draw my spin's punishment, every one as likely, before the dial turns. Repeat-safe: a drawn
    spin comes back as it is. `rng` is for tests."""
    spin = _own(by, spin_id)
    if spin.punishment_id is not None:
        return spin
    punishments = challenges.punishments(challenges=[spin.challenge]).get(spin.challenge_id, [])
    spin.punishment = (rng or secrets.SystemRandom()).choice(punishments)
    spin.drawn_at = clock.now()
    spin.serve_by = clock.crew_today(by.crew) + timedelta(days=SERVE_DAYS)
    spin.save(update_fields=["punishment", "drawn_at", "serve_by", "updated_at"])
    return spin


@transaction.atomic
def mark_done(*, by: Member, spin_id: UUID) -> Spin:
    """Serve a drawn punishment that needs no proof. Repeat-safe."""
    spin = _own(by, spin_id)
    if spin.punishment is None:
        raise NotDrawn()
    if spin.punishment.proof_required:
        raise ProofNeeded()
    if spin.done_at is None:
        spin.done_at = clock.now()
        spin.save(update_fields=["done_at", "updated_at"])
    return spin


def start_proof(
    *,
    by: Member,
    spin_id: UUID,
    kind: str,
    content_type: str,
    size: int,
    fingerprint: str = "",
    thumb_size: int | None = None,
    duration: int | None = None,
) -> proofs.ProofUpload:
    """Add a photo or video to my drawn punishment that needs proof (up to 5; any day). The
    first one the crew can see serves it. It is posted with the spin as it starts (not a draft),
    so it cannot be removed after."""
    with transaction.atomic():
        spin = _own(by, spin_id)  # locked: one start at a time counts the proofs
        if spin.punishment is None:
            raise NotDrawn()
        if not spin.punishment.proof_required:
            raise ProofNotNeeded()
        return proofs.start_proof(
            member=by,
            subject=spin,
            kind=kind,
            content_type=content_type,
            size=size,
            expires_at=clock.now() + UPLOAD_TIME,
            fingerprint=fingerprint,
            thumb_size=thumb_size,
            duration=duration,
            post_id=spin.pk,
        )


def resume_proof(*, by: Member, spin_id: UUID, fingerprint: str) -> proofs.ProofUpload:
    """My video upload still open for this file on this spin."""
    return proofs.resume_proof(
        by=by, fingerprint=fingerprint, subjects=Spin.objects.filter(pk=spin_id, member=by)
    )
