"""What the app needs from object storage, independent of AWS.

The browser uploads file parts straight to storage with presigned URLs; the API only starts,
signs, completes, and verifies uploads. Services depend on `ObjectStorage`, never on boto3.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass

# S3 multipart limits (https://docs.aws.amazon.com/AmazonS3/latest/userguide/qfacts.html).
MIN_PART_NUMBER = 1
MAX_PART_NUMBER = 10_000
MIN_PART_SIZE = 5 * 1024 * 1024  # every part except the last
MAX_PART_SIZE = 5 * 1024 * 1024 * 1024
DEFAULT_PRESIGN_SECONDS = 60 * 60


class StorageError(Exception):
    """Storage failed or rejected the request."""


class UploadNotFound(StorageError):
    """The multipart upload does not exist (completed, aborted, or expired)."""


class InvalidPart(StorageError):
    """A part number is out of range, or a completed part does not match what was uploaded."""


@dataclass(frozen=True, slots=True)
class UploadedPart:
    part_number: int
    etag: str
    size: int | None = None


@dataclass(frozen=True, slots=True)
class ObjectInfo:
    key: str
    size: int
    content_type: str | None
    etag: str | None


class ObjectStorage(ABC):
    """Upload operations on one bucket: one PUT for small files, multipart for big ones."""

    @abstractmethod
    def presign_put(
        self, *, key: str, content_type: str, expires_in: int = DEFAULT_PRESIGN_SECONDS
    ) -> str:
        """Return a URL the browser can PUT a whole file to, sending this Content-Type."""

    @abstractmethod
    def presign_get(self, *, key: str, expires_in: int = DEFAULT_PRESIGN_SECONDS) -> str:
        """Return a URL the browser can read an object from (an <img> or <video> source)."""

    @abstractmethod
    def create_multipart(self, *, key: str, content_type: str) -> str:
        """Start a multipart upload and return its upload id."""

    @abstractmethod
    def presign_part(
        self,
        *,
        key: str,
        upload_id: str,
        part_number: int,
        expires_in: int = DEFAULT_PRESIGN_SECONDS,
    ) -> str:
        """Return a URL the browser can PUT one part to."""

    @abstractmethod
    def list_parts(self, *, key: str, upload_id: str) -> list[UploadedPart]:
        """Parts already uploaded, ordered by part number (used to resume)."""

    @abstractmethod
    def complete_multipart(
        self, *, key: str, upload_id: str, parts: Sequence[UploadedPart]
    ) -> ObjectInfo:
        """Assemble the parts into one object and return its metadata."""

    @abstractmethod
    def abort_multipart(self, *, key: str, upload_id: str) -> None:
        """Cancel an upload and free its parts. Safe to call twice."""

    @abstractmethod
    def head(self, *, key: str) -> ObjectInfo | None:
        """Metadata of a stored object, or None when it does not exist."""

    @abstractmethod
    def delete(self, *, key: str) -> None:
        """Remove an object. Safe to call when it does not exist."""

    @abstractmethod
    def list_keys(self, *, prefix: str) -> list[str]:
        """Keys of the objects under a prefix, sorted."""

    @abstractmethod
    def delete_prefix(self, *, prefix: str) -> None:
        """Remove every object under a prefix (a video's renditions). Safe when there are none."""


def validate_part_number(part_number: int) -> None:
    if not MIN_PART_NUMBER <= part_number <= MAX_PART_NUMBER:
        raise InvalidPart(
            f"Part number must be between {MIN_PART_NUMBER} and {MAX_PART_NUMBER}, "
            f"got {part_number}."
        )


def sorted_parts(parts: Sequence[UploadedPart]) -> list[UploadedPart]:
    """Parts ordered by number; rejects an empty list and duplicate numbers."""
    if not parts:
        raise InvalidPart("At least one part is required.")
    numbers = [p.part_number for p in parts]
    if len(numbers) != len(set(numbers)):
        raise InvalidPart("Duplicate part numbers.")
    for number in numbers:
        validate_part_number(number)
    return sorted(parts, key=lambda p: p.part_number)
