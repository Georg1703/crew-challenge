"""ObjectStorage on Amazon S3. The only module that talks to S3."""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from typing import TYPE_CHECKING

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from .base import (
    DEFAULT_PRESIGN_SECONDS,
    InvalidPart,
    ObjectInfo,
    ObjectStorage,
    StorageError,
    UploadedPart,
    UploadNotFound,
    sorted_parts,
    validate_part_number,
)

if TYPE_CHECKING:
    from mypy_boto3_s3 import S3Client

_NOT_FOUND_CODES = {"NoSuchUpload", "NoSuchKey", "404"}


def make_s3_client(*, region: str, profile: str | None = None) -> S3Client:
    """S3 client with SigV4 and the regional endpoint (needed for eu-central-1 presigning)."""
    session = boto3.Session(profile_name=profile, region_name=region)
    return session.client(
        "s3",
        config=Config(
            signature_version="s3v4",
            s3={"addressing_style": "virtual"},
            retries={"max_attempts": 5, "mode": "standard"},
        ),
    )


class S3ObjectStorage(ObjectStorage):
    def __init__(self, *, bucket: str, client: S3Client) -> None:
        self.bucket = bucket
        self.client = client

    def presign_put(
        self, *, key: str, content_type: str, expires_in: int = DEFAULT_PRESIGN_SECONDS
    ) -> str:
        # ContentType is signed: the browser must send the same Content-Type header.
        return self.client.generate_presigned_url(
            "put_object",
            Params={"Bucket": self.bucket, "Key": key, "ContentType": content_type},
            ExpiresIn=expires_in,
            HttpMethod="PUT",
        )

    def create_multipart(self, *, key: str, content_type: str) -> str:
        with _translate_errors():
            response = self.client.create_multipart_upload(
                Bucket=self.bucket, Key=key, ContentType=content_type
            )
        return response["UploadId"]

    def presign_part(
        self,
        *,
        key: str,
        upload_id: str,
        part_number: int,
        expires_in: int = DEFAULT_PRESIGN_SECONDS,
    ) -> str:
        validate_part_number(part_number)
        return self.client.generate_presigned_url(
            "upload_part",
            Params={
                "Bucket": self.bucket,
                "Key": key,
                "UploadId": upload_id,
                "PartNumber": part_number,
            },
            ExpiresIn=expires_in,
            HttpMethod="PUT",
        )

    def list_parts(self, *, key: str, upload_id: str) -> list[UploadedPart]:
        parts: list[UploadedPart] = []
        marker = 0
        with _translate_errors():
            while True:
                response = self.client.list_parts(
                    Bucket=self.bucket, Key=key, UploadId=upload_id, PartNumberMarker=marker
                )
                parts.extend(
                    UploadedPart(part_number=p["PartNumber"], etag=p["ETag"], size=p.get("Size"))
                    for p in response.get("Parts", [])
                )
                if not response.get("IsTruncated"):
                    break
                marker = response["NextPartNumberMarker"]
        return sorted(parts, key=lambda p: p.part_number)

    def complete_multipart(
        self, *, key: str, upload_id: str, parts: Sequence[UploadedPart]
    ) -> ObjectInfo:
        ordered = sorted_parts(parts)
        with _translate_errors():
            self.client.complete_multipart_upload(
                Bucket=self.bucket,
                Key=key,
                UploadId=upload_id,
                MultipartUpload={
                    "Parts": [{"PartNumber": p.part_number, "ETag": p.etag} for p in ordered]
                },
            )
        info = self.head(key=key)
        if info is None:  # pragma: no cover - S3 guarantees read-after-write
            raise StorageError(f"Object {key!r} missing right after completing its upload.")
        return info

    def abort_multipart(self, *, key: str, upload_id: str) -> None:
        try:
            self.client.abort_multipart_upload(Bucket=self.bucket, Key=key, UploadId=upload_id)
        except ClientError as exc:
            if _error_code(exc) not in _NOT_FOUND_CODES:
                raise StorageError(str(exc)) from exc

    def head(self, *, key: str) -> ObjectInfo | None:
        try:
            response = self.client.head_object(Bucket=self.bucket, Key=key)
        except ClientError as exc:
            if _error_code(exc) in _NOT_FOUND_CODES:
                return None
            raise StorageError(str(exc)) from exc
        return ObjectInfo(
            key=key,
            size=response["ContentLength"],
            content_type=response.get("ContentType"),
            etag=response.get("ETag"),
        )

    def delete(self, *, key: str) -> None:
        with _translate_errors():
            self.client.delete_object(Bucket=self.bucket, Key=key)  # S3 answers 204 when missing


def _error_code(exc: ClientError) -> str:
    return str(exc.response.get("Error", {}).get("Code", ""))


@contextmanager
def _translate_errors() -> Iterator[None]:
    """Turn botocore errors into storage errors the app understands."""
    try:
        yield
    except ClientError as exc:
        code = _error_code(exc)
        if code in _NOT_FOUND_CODES:
            raise UploadNotFound(str(exc)) from exc
        if code in {"InvalidPart", "InvalidPartOrder", "EntityTooSmall"}:
            raise InvalidPart(str(exc)) from exc
        raise StorageError(str(exc)) from exc
