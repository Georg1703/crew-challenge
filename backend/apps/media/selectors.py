"""Media reads: where the browser fetches finished files, and the cookies that let it.

Production: CloudFront URLs, opened for one crew by signed cookies (`media_session`). Local
development: presigned GET URLs, and videos play as uploaded (a presigned URL cannot sign the
segments an HLS playlist points to). Screens never see the difference.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from apps.core import clock
from apps.crews.models import Crew
from integrations.cdn import get_cdn
from integrations.storage import get_object_storage
from integrations.transcoding import get_transcoder

from .models import Transcode, Upload, crew_folder

VIEW_SECONDS = 12 * 60 * 60  # presigned links: long enough for a screen left open
SESSION_LENGTH = timedelta(hours=24)  # the app asks for new cookies before this


def _link(key: str) -> str:
    cdn = get_cdn()
    if cdn is not None:
        return cdn.url(key)
    return get_object_storage().presign_get(key=key, expires_in=VIEW_SECONDS)


def url(upload: Upload | None) -> str | None:
    """A URL for <img> or <video>, or None while the file is not complete."""
    if upload is None or upload.status != Upload.Status.COMPLETE or upload.is_deleted:
        return None
    return _link(upload.key)


def renditions(upload: Upload | None) -> tuple[str | None, str | None]:
    """A finished video's HLS playlist (only through the CDN) and poster, or Nones."""
    job: Transcode | None = getattr(upload, "transcode", None)
    if job is None or job.status != Transcode.Status.DONE:
        return None, None
    cdn = get_cdn()
    hls = cdn.url(job.hls_key) if cdn is not None else None
    return hls, _link(job.poster_key) if job.poster_key else None


def transcoding() -> bool:
    """Whether finished videos get renditions; when off they play as uploaded."""
    return get_transcoder() is not None


@dataclass(frozen=True)
class MediaSession:
    cookies: dict[str, str]
    domain: str
    expires_at: datetime


def media_session(*, crew: Crew) -> MediaSession | None:
    """CloudFront cookies opening the crew's folder for a day; None without a CDN (locally)."""
    cdn = get_cdn()
    if cdn is None:
        return None
    expires_at = clock.now() + SESSION_LENGTH
    cookies = cdn.cookies(prefix=crew_folder(crew.pk), expires_at=expires_at)
    return MediaSession(cookies=cookies, domain=cdn.cookie_domain, expires_at=expires_at)
