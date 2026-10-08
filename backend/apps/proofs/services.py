"""Proof rules that hold for every subject: files, sizes, at most 5, uploads, removal, expiry.

The subject's app checks its own rules first (a check-in: today, checked in) and locks the
subject's row, then calls `start_proof`. A photo takes one PUT; a video a resumable multipart
upload. A proof is removable on the crew-local day it was added; after midnight it is kept.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from django.contrib.contenttypes.models import ContentType
from django.db import models, transaction

from apps.core import clock
from apps.core.errors import Conflict, DomainError, NotFound, ValidationFailed
from apps.crews.models import Member
from apps.media import selectors as media_links
from apps.media import services as media
from apps.media.models import MiB, Transcode, Upload, crew_folder

from .models import Proof

logger = logging.getLogger(__name__)

MAX_PROOFS = 5  # per subject, not counting failed ones
PHOTO_MAX_SIZE = 50 * MiB  # phones send ~0.5 MB after shrinking; this is for originals
THUMB_MAX_SIZE = 2 * MiB
VIDEO_MAX_SECONDS = 3 * 60 * 60  # a video's length, as the phone reads it
EXTENSIONS: dict[str, dict[str, str]] = {  # allowed content types, the extension each gets
    Proof.Kind.PHOTO: {
        "image/jpeg": "jpg",
        "image/png": "png",
        "image/webp": "webp",
        "image/heic": "heic",
    },
    Proof.Kind.VIDEO: {"video/mp4": "mp4", "video/quicktime": "mov", "video/webm": "webm"},
}


class TooManyProofs(Conflict):
    code = "too_many_proofs"
    message = "There can be at most 5 proofs."


class ProofNotFound(NotFound):
    code = "proof_not_found"
    message = "This proof does not exist."


class ProofKept(Conflict):
    code = "day_closed"
    message = "That day has ended; its proofs are kept."


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
        Proof.objects.filter(pk=proof_id, member=by)
        .select_related("original__transcode", "thumb")
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


def of_subject(subject: models.Model) -> models.QuerySet[Proof]:
    return Proof.objects.filter(
        subject_type=ContentType.objects.get_for_model(subject), subject_id=subject.pk
    )


def start_proof(
    *,
    member: Member,
    subject: models.Model,
    kind: str,
    content_type: str,
    size: int,
    expires_at: datetime,
    fingerprint: str = "",
    thumb_size: int | None = None,
    duration: int | None = None,
) -> ProofUpload:
    """Add a photo or video to `subject`, whose row the caller has locked (so two starts at once
    count right). The files must arrive before `expires_at`.

    `thumb_size` announces a small JPEG made on the phone (a video's poster frame); `duration`
    is a video's length in seconds, read on the phone (kept for videos only).
    """
    content_type = content_type.split(";")[0].strip().lower()  # "video/webm;codecs=vp9"
    extension = EXTENSIONS.get(kind, {}).get(content_type)
    if extension is None:
        raise ValidationFailed(fields={"content_type": ["This file type is not supported."]})
    if kind == Proof.Kind.PHOTO and size > PHOTO_MAX_SIZE:
        raise ValidationFailed(fields={"size": ["A photo can be at most 50 MB."]})
    if thumb_size is not None and not 0 < thumb_size <= THUMB_MAX_SIZE:
        raise ValidationFailed(fields={"thumb_size": ["A thumbnail can be at most 2 MB."]})
    if duration is not None and not 0 < duration <= VIDEO_MAX_SECONDS:
        raise ValidationFailed(fields={"duration": ["A video can be at most 3 hours long."]})
    with transaction.atomic():
        if of_subject(subject).exclude(status=Proof.Status.FAILED).count() >= MAX_PROOFS:
            raise TooManyProofs()
        proof_id = uuid.uuid4()
        folder = f"{crew_folder(member.crew_id)}proofs/{proof_id}"
        original = media.start_upload(
            crew=member.crew,
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
                crew=member.crew,
                key=f"{folder}/thumb.jpg",
                content_type="image/jpeg",
                size=thumb_size,
                mode=Upload.Mode.SINGLE,
                expires_at=expires_at,
            )
        proof = Proof.objects.create(
            id=proof_id,
            crew=member.crew,
            member=member,
            subject_type=ContentType.objects.get_for_model(subject),
            subject_id=subject.pk,
            kind=kind,
            original=original,
            thumb=thumb,
            duration=duration if kind == Proof.Kind.VIDEO else None,
        )
    return _upload(proof)


def resume_proof(
    *, by: Member, fingerprint: str, subjects: models.QuerySet[models.Model]
) -> ProofUpload:
    """My video upload still open for this file (name, size, lastModified) on one of `subjects`
    (say, my check-ins of one challenge, so a file picked again after midnight still resumes)."""
    proof = (
        Proof.objects.filter(
            member=by,
            subject_type=ContentType.objects.get_for_model(subjects.model),
            subject_id__in=subjects.values("pk"),
            status=Proof.Status.UPLOADING,
            original__mode=Upload.Mode.MULTIPART,
            original__status=Upload.Status.UPLOADING,
            original__fingerprint=fingerprint,
            original__expires_at__gt=clock.now(),
        )
        .exclude(original__fingerprint="")
        .select_related("original", "thumb")
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
    """Remove my proof and its files, only on the day it was added; after midnight it is kept."""
    proof = _own(by, proof_id)
    start, end = clock.day_bounds_utc(clock.crew_today(by.crew), by.crew.timezone)
    if not start <= proof.created_at < end:
        raise ProofKept()
    _discard(proof)
    proof.delete()


def discard_files(*, subject: models.Model) -> None:
    """Remove the files of every proof of `subject`, which is being deleted (its
    `GenericRelation` deletes the rows with it)."""
    for proof in of_subject(subject):
        _discard(proof)


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
