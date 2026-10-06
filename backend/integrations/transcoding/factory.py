"""Pick the Transcoder from settings.

TRANSCODER_BACKEND = "mediaconvert" (production; locally to try it), "memory" in tests, "off"
(the default locally): no transcoding, videos play as uploaded.
"""

from __future__ import annotations

from functools import lru_cache

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from .base import Transcoder
from .mediaconvert import MediaConvertTranscoder, make_mediaconvert_client
from .memory import InMemoryTranscoder


@lru_cache(maxsize=1)
def get_transcoder() -> Transcoder | None:
    backend = settings.TRANSCODER_BACKEND
    if backend == "off":
        return None
    if backend == "memory":
        return InMemoryTranscoder()
    if backend == "mediaconvert":
        if not settings.MEDIACONVERT_ROLE_ARN:
            raise ImproperlyConfigured("Set MEDIACONVERT_ROLE_ARN to transcode with MediaConvert.")
        client = make_mediaconvert_client(region=settings.AWS_REGION, profile=settings.AWS_PROFILE)
        return MediaConvertTranscoder(
            client=client, bucket=settings.MEDIA_BUCKET, role_arn=settings.MEDIACONVERT_ROLE_ARN
        )
    raise ImproperlyConfigured(f"Unknown TRANSCODER_BACKEND: {backend!r}")
