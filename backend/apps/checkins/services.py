"""Check-in rules: record today's check-in for a challenge, undo the last entry, add proof.

Only today counts, in the crew's time zone: a request for any other day is refused
(`day_closed`), so a tap at 23:59:59 that arrives after midnight never lands on the new day.
A proof started today may still finish uploading up to `UPLOAD_GRACE` after the day's deadline.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

from django.db import transaction
from django.db.models import Sum

from apps.challenges import selectors as challenges
from apps.challenges.models import Challenge, Participant
from apps.challenges.windows import counts_on
from apps.core import clock
from apps.core.errors import Conflict, DomainError, NotFound, PermissionDenied, ValidationFailed
from apps.crews.models import Member
from apps.media import selectors as media_links
from apps.media import services as media
from apps.media.models import MiB, Transcode, Upload, crew_folder

from . import days
from .models import CheckIn, CheckInEntry, Proof

logger = logging.getLogger(__name__)

AMOUNT_MAX = Decimal(1_000_000)
UPLOAD_GRACE = timedelta(hours=24)
MAX_PROOFS = 5  # per check-in, not counting failed ones
PHOTO_MAX_SIZE = 50 * MiB  # phones send ~0.5 MB after shrinking; this is for originals
THUMB_MAX_SIZE = 2 * MiB
VIDEO_MAX_SECONDS = 3 * 60 * 60  # a video's length, as the phone reads it
KINDS: dict[str, set[str]] = {
    Challenge.ProofKind.PHOTO: {Proof.Kind.PHOTO},
    Challenge.ProofKind.VIDEO: {Proof.Kind.VIDEO},
    Challenge.ProofKind.PHOTO_OR_VIDEO: {Proof.Kind.PHOTO, Proof.Kind.VIDEO},
}
EXTENSIONS: dict[str, dict[str, str]] = {  # allowed content types, the extension each gets
    Proof.Kind.PHOTO: {
        "image/jpeg": "jpg",
        "image/png": "png",
        "image/webp": "webp",
        "image/heic": "heic",
    },
    Proof.Kind.VIDEO: {"video/mp4": "mp4", "video/quicktime": "mov", "video/webm": "webm"},
}


class ChallengeNotFound(NotFound):
    code = "challenge_not_found"
    message = "This challenge does not exist."


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


class TooManyProofs(Conflict):
    code = "too_many_proofs"
    message = "A day takes at most 5 proofs."


class ProofNotFound(NotFound):
    code = "proof_not_found"
    message = "This proof does not exist."


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
        for proof in Proof.objects.filter(check_in=row):
            _discard(proof)  # the check-in goes, and its proofs with it
        row.delete()
        return None
    return _refresh(row)


@dataclass
class ProofUpload:
    """A proof and what the browser needs to send its files."""

    proof: Proof
    put_url: str | None = None  # one PUT for the whole original (photos)
    thumb_put_url: str | None = None
    parts: dict[int, str] = field(default_factory=dict)  # finished parts, to resume a video


def _upload(proof: Proof) -> ProofUpload:
    original, thumb = proof.original, proof.thumb
    plan = ProofUpload(proof=proof, parts={int(n): etag for n, etag in original.parts.items()})
    if original.mode == Upload.Mode.SINGLE:
        plan.put_url = media.sign_put(upload_id=original.pk)
    if thumb is not None and thumb.status == Upload.Status.UPLOADING:
        plan.thumb_put_url = media.sign_put(upload_id=thumb.pk)
    return plan


def _own(by: Member, proof_id: UUID) -> Proof:
    proof = (
        Proof.objects.filter(pk=proof_id, check_in__member=by)
        .select_related("check_in", "original__transcode", "thumb")
        .first()
    )
    if proof is None:
        raise ProofNotFound()
    return proof


def _discard(proof: Proof) -> None:
    """Remove the proof's files, stopping uploads that still run."""
    for upload_id in (proof.original_id, proof.thumb_id):
        if upload_id is not None:
            media.delete_upload(upload_id=upload_id)


def _fail(proof: Proof) -> None:
    _discard(proof)
    proof.status = Proof.Status.FAILED
    proof.save(update_fields=["status", "updated_at"])


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
) -> ProofUpload:
    """Add proof to today's check-in: a photo takes one PUT, a video a resumable multipart upload.

    `thumb_size` announces a small JPEG made on the phone (a video's poster frame); `duration`
    is a video's length in seconds, read on the phone (kept for videos only).
    """
    challenge = _participant(by, challenge_id, day).challenge
    if kind not in KINDS.get(challenge.proof_kind, set()):
        raise ValidationFailed(
            fields={"kind": ["This challenge does not take this kind of proof."]}
        )
    content_type = content_type.split(";")[0].strip().lower()  # "video/webm;codecs=vp9"
    extension = EXTENSIONS[kind].get(content_type)
    if extension is None:
        raise ValidationFailed(fields={"content_type": ["This file type is not supported."]})
    if kind == Proof.Kind.PHOTO and size > PHOTO_MAX_SIZE:
        raise ValidationFailed(fields={"size": ["A photo can be at most 50 MB."]})
    if thumb_size is not None and not 0 < thumb_size <= THUMB_MAX_SIZE:
        raise ValidationFailed(fields={"thumb_size": ["A thumbnail can be at most 2 MB."]})
    if duration is not None and not 0 < duration <= VIDEO_MAX_SECONDS:
        raise ValidationFailed(fields={"duration": ["A video can be at most 3 hours long."]})
    with transaction.atomic():
        check_in = (
            CheckIn.objects.select_for_update()  # one start at a time counts the proofs
            .filter(challenge=challenge, member=by, day=day)
            .first()
        )
        if check_in is None:
            raise NotCheckedIn()
        taken = Proof.objects.filter(check_in=check_in).exclude(status=Proof.Status.FAILED)
        if taken.count() >= MAX_PROOFS:
            raise TooManyProofs()
        proof_id = uuid.uuid4()
        folder = f"{crew_folder(by.crew_id)}proofs/{proof_id}"
        expires_at = clock.deadline_utc(day, by.crew.timezone) + UPLOAD_GRACE
        original = media.start_upload(
            crew=by.crew,
            key=f"{folder}/original.{extension}",
            content_type=content_type,
            size=size,
            mode=Upload.Mode.SINGLE if kind == Proof.Kind.PHOTO else Upload.Mode.MULTIPART,
            expires_at=expires_at,
            fingerprint=fingerprint,
        )
        thumb = None
        if thumb_size is not None:
            thumb = media.start_upload(
                crew=by.crew,
                key=f"{folder}/thumb.jpg",
                content_type="image/jpeg",
                size=thumb_size,
                mode=Upload.Mode.SINGLE,
                expires_at=expires_at,
            )
        proof = Proof.objects.create(
            id=proof_id,
            crew=by.crew,
            check_in=check_in,
            kind=kind,
            original=original,
            thumb=thumb,
            duration=duration if kind == Proof.Kind.VIDEO else None,
        )
    return _upload(proof)


def resume_proof(*, by: Member, fingerprint: str) -> ProofUpload:
    """My video upload still open for this file (name, size, lastModified), with its parts."""
    proof = (
        Proof.objects.filter(
            check_in__member=by,
            status=Proof.Status.UPLOADING,
            original__mode=Upload.Mode.MULTIPART,
            original__status=Upload.Status.UPLOADING,
            original__fingerprint=fingerprint,
            original__expires_at__gt=clock.now(),
        )
        .exclude(original__fingerprint="")
        .select_related("check_in", "original", "thumb")
        .order_by("-created_at")
        .first()
    )
    if proof is None:
        raise ProofNotFound()
    return _upload(proof)


def sign_parts(*, by: Member, proof_id: UUID, numbers: list[int]) -> dict[int, str]:
    return media.sign_parts(upload_id=_own(by, proof_id).original_id, numbers=numbers)


def record_part(*, by: Member, proof_id: UUID, number: int, etag: str) -> None:
    media.record_part(upload_id=_own(by, proof_id).original_id, number=number, etag=etag)


def complete_proof(*, by: Member, proof_id: UUID) -> Proof:
    """Check the uploaded file. A photo is then ready; a video is processing until its renditions
    are made (see `finish_videos`), or ready at once when transcoding is off. Safe to repeat.

    A missing or broken thumbnail is dropped: the original (or the video's poster) stands in.
    """
    proof = _own(by, proof_id)
    if proof.status != Proof.Status.UPLOADING:
        return proof
    try:
        proof.original = media.complete_upload(upload_id=proof.original_id)
    except media.UploadSizeMismatch:
        _fail(proof)
        raise
    if proof.thumb_id is not None:
        try:
            proof.thumb = media.complete_upload(upload_id=proof.thumb_id)
        except DomainError:
            media.delete_upload(upload_id=proof.thumb_id)
            proof.thumb = None
    transcode = proof.kind == Proof.Kind.VIDEO and media_links.transcoding()
    proof.status = Proof.Status.PROCESSING if transcode else Proof.Status.READY
    proof.save(update_fields=["status", "thumb", "updated_at"])
    if transcode:
        from . import tasks  # tasks import services

        transaction.on_commit(tasks.finish_videos.delay)  # start now; beat also checks every 20 s
    return proof


@transaction.atomic
def delete_proof(*, by: Member, proof_id: UUID) -> None:
    """Remove my proof and its files, only on its own day; after midnight proofs are kept."""
    proof = _own(by, proof_id)
    if proof.check_in.day != clock.crew_today(by.crew):
        raise DayClosed("That day has ended; its proofs are kept.")
    _discard(proof)
    proof.delete()


def finish_videos() -> int:
    """Start or check the transcoding of every processing video; show the finished ones.

    Runs every 20 seconds and after each completed video; safe to run twice. A failed or given-up
    job still shows the video: the original plays where the browser can play it.
    """
    finished = 0
    for proof in Proof.objects.filter(status=Proof.Status.PROCESSING):
        try:
            job = media.transcode(upload_id=proof.original_id)
        except media.TranscodeError:
            logger.exception("Transcoding of proof %s could not be started or checked", proof.pk)
            continue
        if job is not None and job.status == Transcode.Status.RUNNING:
            continue
        if job is not None and job.status == Transcode.Status.FAILED:
            logger.warning("Transcoding of proof %s failed: %s", proof.pk, job.error)
        proof.status = Proof.Status.READY
        proof.save(update_fields=["status", "updated_at"])
        finished += 1
    return finished


def expire_proofs() -> int:
    """Fail proofs whose upload ran past its grace, removing what was sent. Safe to run twice."""
    stuck = list(
        Proof.objects.filter(status=Proof.Status.UPLOADING, original__expires_at__lte=clock.now())
    )
    for proof in stuck:
        _fail(proof)
    return len(stuck)
