"""Pick the CDN from settings: CloudFront when MEDIA_CDN_DOMAIN is set (production), else None
(local development and tests read media through presigned URLs instead)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from .cloudfront import CloudFront


@lru_cache(maxsize=1)
def get_cdn() -> CloudFront | None:
    if not settings.MEDIA_CDN_DOMAIN:
        return None
    if not settings.CLOUDFRONT_KEY_PAIR_ID or not settings.CLOUDFRONT_PRIVATE_KEY_PATH:
        raise ImproperlyConfigured(
            "MEDIA_CDN_DOMAIN needs CLOUDFRONT_KEY_PAIR_ID and CLOUDFRONT_PRIVATE_KEY_PATH."
        )
    return CloudFront(
        domain=settings.MEDIA_CDN_DOMAIN,
        key_pair_id=settings.CLOUDFRONT_KEY_PAIR_ID,
        private_key_pem=Path(settings.CLOUDFRONT_PRIVATE_KEY_PATH).read_bytes(),
    )
