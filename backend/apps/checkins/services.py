"""Check-in rules: record today's check-in for a challenge, undo the last entry, add proof.

Only today counts, in the crew's time zone: a request for any other day is refused
(`day_closed`), so a tap at 23:59:59 that arrives after midnight never lands on the new day.
A proof started today may still finish uploading up to `UPLOAD_GRACE` after the day's deadline.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

from django.db import transaction
from django.db.models import Sum

from apps.challenges import selectors as challenges
from apps.challenges.models import Challenge, Participant
from apps.challenges.services import ChallengeNotFound
from apps.challenges.windows import counts_on
from apps.core import clock
from apps.core.errors import Conflict, NotFound, PermissionDenied, ValidationFailed
from apps.crews.models import Member
from apps.proofs import services as proofs

from . import days
from .models import CheckIn, CheckInEntry

AMOUNT_MAX = Decimal(1_000_000)
UPLOAD_GRACE = timedelta(hours=24)


class MemberNotFound(NotFound):
    code = "member_not_found"
    message = "This member is not in your crew."


class DayClosed(Conflict):
    code = "day_closed"
    message = "That day has ended. Only today can be checked in."


class NotTakingPart(PermissionDenied):
    code = "not_taking_part"
    message = "You are not taking part in this challenge today."


class NotDueToday(Conflict):
    code = "not_due_today"
    message = "This challenge does not ask for today."


class NothingToUndo(Conflict):
    code = "nothing_to_undo"
    message = "There is nothing to undo for today."


class NotCheckedIn(Conflict):
    code = "not_checked_in"
    message = "Check in first, then add proof."


def _participant(by: Member, challenge_id: UUID, day: date) -> Participant:
    """The member's participant row that covers today, or the matching error."""
    if day != clock.crew_today(by.crew):
        raise DayClosed()
    challenge = challenges.get_challenge(member=by, challenge_id=challenge_id)
    if challenge is None:
        raise ChallengeNotFound()
    for participant in challenges.participants_on(viewer=by, day=day):
        if participant.challenge_id == challenge.pk and participant.member_id == by.pk:
            return participant
    raise NotTakingPart()


def _clean_amount(challenge: Challenge, amount: Decimal | None) -> Decimal | None:
    if challenge.measure != Challenge.Measure.QUANTITY:
        return None
    if amount is None or not amount.is_finite() or not 0 < amount <= AMOUNT_MAX:
        raise ValidationFailed(fields={"amount": ["Give a number above zero."]})
    return amount


def _refresh(check_in: CheckIn) -> CheckIn:
    """Recompute the total and the status from the entries."""
    total = check_in.entries.aggregate(total=Sum("amount"))["total"]
    check_in.amount = total if check_in.challenge.measure == Challenge.Measure.QUANTITY else None
    check_in.status = (
        CheckIn.Status.DONE
        if days.counts(check_in.challenge, check_in.amount)
        else CheckIn.Status.IN_PROGRESS
    )
    check_in.save(update_fields=["amount", "status", "updated_at"])
    return check_in


@transaction.atomic
def check_in(
    *, by: Member, challenge_id: UUID, day: date, amount: Decimal | None = None
) -> CheckIn:
    """Record today's check-in. Numbers add up during the day; a plain check-in counts once."""
    participant = _participant(by, challenge_id, day)
    challenge = participant.challenge
    if not counts_on(challenge, day):
        raise NotDueToday()
    value = _clean_amount(challenge, amount)
    row, created = CheckIn.objects.select_for_update().get_or_create(
        challenge=challenge,
        member=by,
        day=day,
        defaults={"crew": by.crew, "status": CheckIn.Status.IN_PROGRESS},
    )
    if not created and value is None and row.status == CheckIn.Status.DONE:
        return row  # tapping "done" twice changes nothing
    last = row.entries.order_by("-number").first()
    number = last.number + 1 if last else 1
    CheckInEntry.objects.create(crew=by.crew, check_in=row, number=number, amount=value)
    return _refresh(row)


@transaction.atomic
def undo_last(*, by: Member, challenge_id: UUID, day: date) -> CheckIn | None:
    """Remove today's last entry; the check-in goes with the last one (then None)."""
    participant = _participant(by, challenge_id, day)
    row = (
        CheckIn.objects.select_for_update()
        .filter(challenge=participant.challenge, member=by, day=day)
        .first()
    )
    if row is None:
        raise NothingToUndo()
    last = row.entries.order_by("-number").first()
    if last is not None:
        last.delete()
    if not row.entries.exists():
        proofs.discard_files(subject=row)  # the check-in goes, and its proofs with it
        row.delete()
        return None
    return _refresh(row)


def start_proof(
    *,
    by: Member,
    challenge_id: UUID,
    day: date,
    kind: str,
    content_type: str,
    size: int,
    fingerprint: str = "",
    thumb_size: int | None = None,
    duration: int | None = None,
) -> proofs.ProofUpload:
    """Add a photo or video to today's check-in, on a challenge that asks for proof. Its files
    must arrive within `UPLOAD_GRACE` after the day's deadline."""
    challenge = _participant(by, challenge_id, day).challenge
    if not challenge.proof_required:
        raise ValidationFailed(fields={"kind": ["This challenge takes no proof."]})
    with transaction.atomic():
        check_in = (
            CheckIn.objects.select_for_update()  # one start at a time counts the proofs
            .filter(challenge=challenge, member=by, day=day)
            .first()
        )
        if check_in is None:
            raise NotCheckedIn()
        return proofs.start_proof(
            member=by,
            subject=check_in,
            kind=kind,
            content_type=content_type,
            size=size,
            expires_at=clock.deadline_utc(day, by.crew.timezone) + UPLOAD_GRACE,
            fingerprint=fingerprint,
            thumb_size=thumb_size,
            duration=duration,
        )


def resume_proof(*, by: Member, challenge_id: UUID, fingerprint: str) -> proofs.ProofUpload:
    """My video upload still open for this file on one of my check-ins of this challenge, also
    yesterday's while its grace runs."""
    return proofs.resume_proof(
        by=by,
        fingerprint=fingerprint,
        subjects=CheckIn.objects.filter(challenge_id=challenge_id, member=by),
    )
