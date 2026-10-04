"""Object storage adapter (S3 multipart uploads). See base.py for the interface."""

from .base import (
    MAX_PART_NUMBER,
    MAX_PART_SIZE,
    MIN_PART_SIZE,
    InvalidPart,
    ObjectInfo,
    ObjectStorage,
    StorageError,
    UploadedPart,
    UploadNotFound,
)
from .factory import get_object_storage
from .memory import InMemoryObjectStorage
from .s3 import S3ObjectStorage

__all__ = [
    "MAX_PART_NUMBER",
    "MAX_PART_SIZE",
    "MIN_PART_SIZE",
    "InMemoryObjectStorage",
    "InvalidPart",
    "ObjectInfo",
    "ObjectStorage",
    "S3ObjectStorage",
    "StorageError",
    "UploadNotFound",
    "UploadedPart",
    "get_object_storage",
]
