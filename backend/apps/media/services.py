"""Upload rules: start, sign, record parts, complete, delete; transcode finished videos.

The browser sends bytes straight to the media bucket with presigned URLs; these services only
start, sign, check and finish uploads. Small files (photos) take one PUT; big ones (videos) are
S3 multipart uploads that survive a closed app: every finished part's ETag is recorded here, so
picking the same file again uploads only the missing parts.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timedelta
from uuid import UUID

from django.db import transaction

from apps.core import clock
from apps.core.errors import Conflict, NotFound, ValidationFailed
from apps.crews.models import Crew
from integrations.storage import (
    InvalidPart,
    ObjectInfo,
    UploadedPart,
    get_object_storage,
)
from integrations.storage import UploadNotFound as MultipartGone
from integrations.transcoding import (
    DONE,
    FAILED,
    HLS_PLAYLIST,
    POSTER_PREFIX,
    get_transcoder,
)
from integrations.transcoding import TranscodeError as TranscodeError  # raised by transcode()

from .models import GiB, Transcode, Upload

MAX_SIZE = 20 * GiB
MAX_SINGLE_SIZE = 5 * GiB  # S3's limit for one PUT
MAX_ETAG_LENGTH = 100
TRANSCODE_TIMEOUT = timedelta(hours=2)


class UploadNotFound(NotFound):
    code = "upload_not_found"
    message = "This upload does not exist."


class UploadClosed(Conflict):
    code = "upload_closed"
    message = "This upload has ended. Pick the file again to start over."


class UploadIncomplete(Conflict):
    code = "upload_incomplete"
    message = "The file is not fully uploaded yet."


class UploadSizeMismatch(Conflict):
    code = "upload_size_mismatch"
    message = "The uploaded file is not the one that was announced."


def _get(upload_id: UUID, *, lock: bool = False) -> Upload:
    rows = Upload.objects.filter(pk=upload_id)
    upload = (rows.select_for_update() if lock else rows).first()
    if upload is None:
        raise UploadNotFound()
    return upload


def _require_open(upload: Upload, mode: Upload.Mode | None = None) -> None:
    if upload.status != Upload.Status.UPLOADING or clock.now() >= upload.expires_at:
        raise UploadClosed()
    if mode is not None and upload.mode != mode:
        raise ValidationFailed(f"This upload is not a {mode} upload.")


def _require_part_numbers(upload: Upload, numbers: Sequence[int]) -> None:
    if not numbers or any(not 1 <= n <= upload.part_count for n in numbers):
        raise ValidationFailed(
            fields={"number": [f"Part numbers go from 1 to {upload.part_count}."]}
        )


def start_upload(
    *,
    crew: Crew,
    key: str,
    content_type: str,
    size: int,
    mode: Upload.Mode,
    expires_at: datetime,
    fingerprint: str = "",
) -> Upload:
    """Open an upload. Multipart ones start in storage at once; a single PUT is signed later."""
    limit = MAX_SINGLE_SIZE if mode == Upload.Mode.SINGLE else MAX_SIZE
    if not 0 < size <= limit:
        raise ValidationFailed(fields={"size": [f"The file must be at most {limit // GiB} GiB."]})
    upload_id = ""
    if mode == Upload.Mode.MULTIPART:
        upload_id = get_object_storage().create_multipart(key=key, content_type=content_type)
    return Upload.objects.create(
        crew=crew,
        key=key,
        content_type=content_type,
        size=size,
        mode=mode,
        upload_id=upload_id,
        expires_at=expires_at,
        fingerprint=fingerprint,
    )


def sign_put(*, upload_id: UUID) -> str:
    """A fresh URL for the browser to PUT the whole file to (a single upload)."""
    upload = _get(upload_id)
    _require_open(upload, Upload.Mode.SINGLE)
    return get_object_storage().presign_put(key=upload.key, content_type=upload.content_type)


def sign_parts(*, upload_id: UUID, numbers: Sequence[int]) -> dict[int, str]:
    """Fresh URLs for the browser to PUT these parts to (also when earlier ones expired)."""
    upload = _get(upload_id)
    _require_open(upload, Upload.Mode.MULTIPART)
    _require_part_numbers(upload, numbers)
    storage = get_object_storage()
    return {
        n: storage.presign_part(key=upload.key, upload_id=upload.upload_id, part_number=n)
        for n in sorted(set(numbers))
    }


@transaction.atomic
def record_part(*, upload_id: UUID, number: int, etag: str) -> Upload:
    """Remember a finished part. Reporting the same part again replaces its ETag."""
    upload = _get(upload_id, lock=True)  # parts arrive in parallel: one writer at a time
    _require_open(upload, Upload.Mode.MULTIPART)
    _require_part_numbers(upload, [number])
    if not etag or len(etag) > MAX_ETAG_LENGTH:
        raise ValidationFailed(fields={"etag": ["Send the ETag S3 returned for this part."]})
    upload.parts[str(number)] = etag
    upload.save(update_fields=["parts", "updated_at"])
    return upload


def _assemble(upload: Upload) -> ObjectInfo | None:
    """Put the file together in storage; None while parts (or the single PUT) are missing."""
    storage = get_object_storage()
    if upload.mode == Upload.Mode.MULTIPART:
        parts = [UploadedPart(part_number=int(n), etag=etag) for n, etag in upload.parts.items()]
        if len(parts) < upload.part_count:
            return None
        try:
            return storage.complete_multipart(
                key=upload.key, upload_id=upload.upload_id, parts=parts
            )
        except InvalidPart:
            return None  # S3 does not hold a part with that ETag
        except MultipartGone:
            pass  # completed by an earlier request whose answer was lost: the file is there
    return storage.head(key=upload.key)


def complete_upload(*, upload_id: UUID) -> Upload:
    """Finish the upload and check the file's size. Calling it again after success is a no-op.

    A file of another size than announced is deleted and the upload fails.
    """
    # ponytail: S3 assembles in the request (seconds for ~300 parts); move it to Celery if
    # completing big videos ever outlives the gunicorn timeout.
    with transaction.atomic():
        upload = _get(upload_id, lock=True)
        if upload.status == Upload.Status.COMPLETE:
            return upload
        _require_open(upload)
        info = _assemble(upload)
        if info is None:
            raise UploadIncomplete()
        if info.size == upload.size:
            upload.status = Upload.Status.COMPLETE
            upload.completed_at = clock.now()
        else:
            get_object_storage().delete(key=upload.key)
            upload.status = Upload.Status.FAILED
        upload.save(update_fields=["status", "completed_at", "updated_at"])
    if upload.status == Upload.Status.FAILED:
        raise UploadSizeMismatch()
    return upload


@transaction.atomic
def delete_upload(*, upload_id: UUID) -> None:
    """Remove the file (stopping its upload if it runs) and soft-delete the row. Safe twice."""
    upload = Upload.objects.select_for_update().filter(pk=upload_id).first()
    if upload is None:
        return
    storage = get_object_storage()
    if upload.mode == Upload.Mode.MULTIPART and upload.status == Upload.Status.UPLOADING:
        storage.abort_multipart(key=upload.key, upload_id=upload.upload_id)
    storage.delete(key=upload.key)
    if Transcode.objects.filter(upload=upload).exists():
        # ponytail: a job still running may write after this; cancel it if leftovers ever matter.
        storage.delete_prefix(prefix=upload.renditions_prefix)
    upload.delete()


def transcode(*, upload_id: UUID) -> Transcode | None:
    """Start the job that makes a finished video's renditions, or check the one running.

    Call it as often as you like: one job per upload, ever. None when transcoding is off (the
    video plays as uploaded). A job still running after 2 hours is given up. Raises
    TranscodeError when the service cannot be reached; try again later.
    """
    transcoder = get_transcoder()
    if transcoder is None:
        return None
    with transaction.atomic():
        upload = _get(upload_id, lock=True)  # two pollers never start two jobs
        if upload.status != Upload.Status.COMPLETE:
            raise UploadIncomplete()
        job = Transcode.objects.filter(upload=upload).first()
        if job is None:
            job_id = transcoder.start(input_key=upload.key, output_prefix=upload.renditions_prefix)
            return Transcode.objects.create(crew_id=upload.crew_id, upload=upload, job_id=job_id)
        if job.status != Transcode.Status.RUNNING:
            return job
        state = transcoder.check(job_id=job.job_id)
        if state.state == DONE:
            prefix = upload.renditions_prefix
            posters = get_object_storage().list_keys(prefix=prefix + POSTER_PREFIX)
            job.status = Transcode.Status.DONE
            job.hls_key = prefix + HLS_PLAYLIST
            job.poster_key = posters[0] if posters else ""
        elif state.state == FAILED or clock.now() >= job.created_at + TRANSCODE_TIMEOUT:
            job.status = Transcode.Status.FAILED
            job.error = (state.error or "Gave up after 2 hours.")[:500]
        else:
            return job
        job.save(update_fields=["status", "hls_key", "poster_key", "error", "updated_at"])
    return job
