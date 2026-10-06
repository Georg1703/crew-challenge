"""ObjectStorage kept in memory, for tests. Mirrors the S3 behavior services rely on."""

from __future__ import annotations

import hashlib
import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field

from .base import (
    DEFAULT_PRESIGN_SECONDS,
    MIN_PART_SIZE,
    InvalidPart,
    ObjectInfo,
    ObjectStorage,
    UploadedPart,
    UploadNotFound,
    sorted_parts,
    validate_part_number,
)


@dataclass
class _PendingUpload:
    key: str
    content_type: str
    parts: dict[int, bytes] = field(default_factory=dict)


@dataclass
class _StoredObject:
    data: bytes
    content_type: str
    etag: str


def _etag(data: bytes) -> str:
    return f'"{hashlib.md5(data, usedforsecurity=False).hexdigest()}"'


class InMemoryObjectStorage(ObjectStorage):
    """Use `upload_part()` in tests to play the browser's role."""

    def __init__(self, *, bucket: str = "memory") -> None:
        self.bucket = bucket
        self.uploads: dict[str, _PendingUpload] = {}
        self.objects: dict[str, _StoredObject] = {}

    # --- test helpers ------------------------------------------------------------------------
    def put_object(self, *, key: str, data: bytes, content_type: str) -> str:
        """Store a whole file as the browser would via its presigned PUT URL; returns the ETag."""
        self.objects[key] = _StoredObject(data=data, content_type=content_type, etag=_etag(data))
        return self.objects[key].etag

    def upload_part(self, *, key: str, upload_id: str, part_number: int, data: bytes) -> str:
        """Store one part as the browser would via its presigned URL; returns the ETag."""
        validate_part_number(part_number)
        upload = self._pending(key, upload_id)
        upload.parts[part_number] = data
        return _etag(data)

    # --- ObjectStorage -----------------------------------------------------------------------
    def presign_put(
        self, *, key: str, content_type: str, expires_in: int = DEFAULT_PRESIGN_SECONDS
    ) -> str:
        return f"memory://{self.bucket}/{key}?contentType={content_type}&expires={expires_in}"

    def presign_get(self, *, key: str, expires_in: int = DEFAULT_PRESIGN_SECONDS) -> str:
        return f"memory://{self.bucket}/{key}?expires={expires_in}"

    def create_multipart(self, *, key: str, content_type: str) -> str:
        upload_id = uuid.uuid4().hex
        self.uploads[upload_id] = _PendingUpload(key=key, content_type=content_type)
        return upload_id

    def presign_part(
        self,
        *,
        key: str,
        upload_id: str,
        part_number: int,
        expires_in: int = DEFAULT_PRESIGN_SECONDS,
    ) -> str:
        validate_part_number(part_number)
        self._pending(key, upload_id)
        return (
            f"memory://{self.bucket}/{key}?uploadId={upload_id}"
            f"&partNumber={part_number}&expires={expires_in}"
        )

    def list_parts(self, *, key: str, upload_id: str) -> list[UploadedPart]:
        upload = self._pending(key, upload_id)
        return [
            UploadedPart(part_number=n, etag=_etag(data), size=len(data))
            for n, data in sorted(upload.parts.items())
        ]

    def complete_multipart(
        self, *, key: str, upload_id: str, parts: Sequence[UploadedPart]
    ) -> ObjectInfo:
        ordered = sorted_parts(parts)
        upload = self._pending(key, upload_id)
        chunks: list[bytes] = []
        for index, part in enumerate(ordered):
            data = upload.parts.get(part.part_number)
            if data is None or _etag(data) != part.etag:
                raise InvalidPart(f"Part {part.part_number} was not uploaded or its ETag differs.")
            if index < len(ordered) - 1 and len(data) < MIN_PART_SIZE:
                raise InvalidPart(f"Part {part.part_number} is smaller than 5 MiB.")
            chunks.append(data)
        body = b"".join(chunks)
        self.objects[key] = _StoredObject(
            data=body, content_type=upload.content_type, etag=_etag(body)
        )
        del self.uploads[upload_id]
        return self._info(key)

    def abort_multipart(self, *, key: str, upload_id: str) -> None:
        upload = self.uploads.get(upload_id)
        if upload is not None and upload.key == key:
            del self.uploads[upload_id]

    def head(self, *, key: str) -> ObjectInfo | None:
        return self._info(key) if key in self.objects else None

    def delete(self, *, key: str) -> None:
        self.objects.pop(key, None)

    def list_keys(self, *, prefix: str) -> list[str]:
        return sorted(k for k in self.objects if k.startswith(prefix))

    def delete_prefix(self, *, prefix: str) -> None:
        for key in self.list_keys(prefix=prefix):
            del self.objects[key]

    # --- internals ---------------------------------------------------------------------------
    def _pending(self, key: str, upload_id: str) -> _PendingUpload:
        upload = self.uploads.get(upload_id)
        if upload is None or upload.key != key:
            raise UploadNotFound(f"No multipart upload {upload_id!r} for {key!r}.")
        return upload

    def _info(self, key: str) -> ObjectInfo:
        obj = self.objects[key]
        return ObjectInfo(key=key, size=len(obj.data), content_type=obj.content_type, etag=obj.etag)
