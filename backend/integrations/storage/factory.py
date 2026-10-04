"""Pick the ObjectStorage implementation from settings.

OBJECT_STORAGE_BACKEND = "s3" everywhere real; "memory" in tests. Call get_object_storage()
from services; never construct an implementation directly outside this package and tests.
"""

from __future__ import annotations

from functools import lru_cache

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from .base import ObjectStorage
from .memory import InMemoryObjectStorage
from .s3 import S3ObjectStorage, make_s3_client


@lru_cache(maxsize=1)
def get_object_storage() -> ObjectStorage:
    backend = settings.OBJECT_STORAGE_BACKEND
    if backend == "memory":
        return InMemoryObjectStorage(bucket=settings.MEDIA_BUCKET)
    if backend == "s3":
        client = make_s3_client(region=settings.AWS_REGION, profile=settings.AWS_PROFILE)
        return S3ObjectStorage(bucket=settings.MEDIA_BUCKET, client=client)
    raise ImproperlyConfigured(f"Unknown OBJECT_STORAGE_BACKEND: {backend!r}")
