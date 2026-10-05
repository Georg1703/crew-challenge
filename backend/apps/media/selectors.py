"""Media reads: where the browser can fetch a finished file."""

from __future__ import annotations

from integrations.storage import get_object_storage

from .models import Upload

VIEW_SECONDS = 12 * 60 * 60  # long enough for a screen left open; refetched with its data


def url(upload: Upload | None) -> str | None:
    """A URL for <img> or <video>, or None while the file is not complete.

    Presigned GET for now; production moves to CloudFront with signed cookies (stage 3 of the
    proof upload plan) behind this same function.
    """
    if upload is None or upload.status != Upload.Status.COMPLETE or upload.is_deleted:
        return None
    return get_object_storage().presign_get(key=upload.key, expires_in=VIEW_SECONDS)
