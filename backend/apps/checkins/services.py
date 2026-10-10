"""Check-in rules: post (a check-in, a "+N", photos or videos added later), undo the latest
post, upload draft files.

Only today counts, in the crew's time zone: a request for any other day is refused
(`day_closed`), so a tap at 23:59:59 that arrives after midnight never lands on the new day.
Photos and videos upload first, as draft files on the day's check-in (`pending` while it has no
post); a post publishes the uploaded ones. Midnight ends the day for its draft files too: not
posted by then, they expire with it.
"""

from __future__ import annotations

from datetime import date
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
from apps.proofs.models import Proof
from apps.proofs.selectors import SHOWN

from . import days
from .models import CheckIn, CheckInEntry

AMOUNT_MAX = Decimal(1_000_000)


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


class UploadsRunning(Conflict):
    code = "uploads_running"
    message = "Wait for the photos and videos to finish uploading."


class ProofRequired(Conflict):
    code = "proof_required"
    message = "This challenge asks for a photo or a video with each check-in."


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
    """Recompute the total and the status from the posts (`pending`: only draft files so far)."""
    total = check_in.entries.aggregate(total=Sum("amount"))["total"]
    check_in.amount = total if check_in.challenge.measure == Challenge.Measure.QUANTITY else None
    check_in.status = (
        CheckIn.Status.PENDING
        if not check_in.entries.exists()
        else CheckIn.Status.DONE
        if days.counts(check_in.challenge, check_in.amount)
        else CheckIn.Status.IN_PROGRESS
    )
    check_in.save(update_fields=["amount", "status", "updated_at"])
    return check_in


def _day_row(by: Member, challenge: Challenge, day: date) -> CheckIn:
    """My check-in of that day, locked (made `pending` when there is none yet)."""
    # ponytail: a pending check-in whose draft files all went stays behind, skipped by every read;
    # sweep them in a beat task if they ever pile up.
    row, _ = CheckIn.objects.select_for_update().get_or_create(
        challenge=challenge,
        member=by,
        day=day,
        defaults={"crew": by.crew, "status": CheckIn.Status.PENDING},
    )
    return row


@transaction.atomic
def check_in(
    *, by: Member, challenge_id: UUID, day: date, amount: Decimal | None = None
) -> CheckIn:
    """Post: today's check-in, a "+N", or photos and videos added later, with the day's uploaded
    draft files. Numbers add up during the day. Whether a post counts follows from what it is: a
    "+N" has a number; on other challenges the day's first post is the check-in and later ones
    only add files (a second tap with nothing to add changes nothing)."""
    participant = _participant(by, challenge_id, day)
    challenge = participant.challenge
    if not counts_on(challenge, day):
        raise NotDueToday()
    quantity = challenge.measure == Challenge.Measure.QUANTITY
    value = _clean_amount(challenge, amount) if amount is not None else None
    row = _day_row(by, challenge, day)
    drafts = list(proofs.drafts(subject=row))
    if any(p.status == Proof.Status.UPLOADING for p in drafts):
        raise UploadsRunning()
    files = sum(p.status in SHOWN for p in drafts)
    last = row.entries.order_by("-number").first()
    if quantity and last is None and value is None:
        raise ValidationFailed(fields={"amount": ["Give a number above zero."]})
    counting = value is not None if quantity else last is None
    if counting and challenge.proof_required and not files:
        raise ProofRequired()
    if not counting and not files:
        return row  # nothing to post
    entry = CheckInEntry.objects.create(
        crew=by.crew, check_in=row, number=last.number + 1 if last else 1, amount=value
    )
    proofs.publish(subject=row, post_id=entry.pk)
    return _refresh(row)


@transaction.atomic
def undo_last(*, by: Member, challenge_id: UUID, day: date) -> CheckIn | None:
    """Delete today's latest post with its files. The check-in goes with its last post (then
    None), unless draft files still wait on it (then it is `pending` again)."""
    participant = _participant(by, challenge_id, day)
    row = (
        CheckIn.objects.select_for_update()
        .filter(challenge=participant.challenge, member=by, day=day)
        .first()
    )
    last = row.entries.order_by("-number").first() if row is not None else None
    if row is None or last is None:
        raise NothingToUndo()
    proofs.remove_post(subject=row, post_id=last.pk)
    last.delete()
    if row.entries.exists() or proofs.drafts(subject=row).exists():
        return _refresh(row)
    row.delete()
    return None


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
    """Upload a photo or video as a draft file of today's check-in, on any challenge due today; the
    next post publishes it. Its files must arrive, and be posted, before the day's deadline."""
    challenge = _participant(by, challenge_id, day).challenge
    if not counts_on(challenge, day):
        raise NotDueToday()
    with transaction.atomic():
        return proofs.start_proof(
            member=by,
            subject=_day_row(by, challenge, day),  # locked: one start at a time counts the files
            kind=kind,
            content_type=content_type,
            size=size,
            expires_at=clock.deadline_utc(day, by.crew.timezone),
            fingerprint=fingerprint,
            thumb_size=thumb_size,
            duration=duration,
        )


def resume_proof(*, by: Member, challenge_id: UUID, fingerprint: str) -> proofs.ProofUpload:
    """My video upload still open for this file on today's check-in of this challenge."""
    return proofs.resume_proof(
        by=by,
        fingerprint=fingerprint,
        subjects=CheckIn.objects.filter(challenge_id=challenge_id, member=by),
    )
