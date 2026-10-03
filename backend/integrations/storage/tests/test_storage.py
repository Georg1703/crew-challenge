"""Contract tests: the S3 adapter (against moto) and the in-memory fake behave the same way."""

from collections.abc import Iterator
from typing import Final
from urllib.parse import parse_qs, urlparse

import pytest
from botocore.exceptions import ClientError
from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings
from moto import mock_aws

from integrations.storage import (
    MIN_PART_SIZE,
    InMemoryObjectStorage,
    InvalidPart,
    ObjectStorage,
    S3ObjectStorage,
    StorageError,
    UploadedPart,
    UploadNotFound,
    get_object_storage,
)
from integrations.storage.base import sorted_parts
from integrations.storage.s3 import make_s3_client

REGION: Final = "eu-central-1"
BUCKET = "cc-test-media"
KEY = "originals/crew-1/proof-1.mp4"


@pytest.fixture(params=["memory", "s3"])
def storage(request) -> Iterator[ObjectStorage]:
    if request.param == "memory":
        yield InMemoryObjectStorage(bucket=BUCKET)
        return
    with mock_aws():
        client = make_s3_client(region=REGION)
        client.create_bucket(
            Bucket=BUCKET, CreateBucketConfiguration={"LocationConstraint": REGION}
        )
        yield S3ObjectStorage(bucket=BUCKET, client=client)


def put_part(storage: ObjectStorage, upload_id: str, number: int, data: bytes) -> UploadedPart:
    """Play the browser: upload one part and return what it reports to the API."""
    if isinstance(storage, InMemoryObjectStorage):
        etag = storage.upload_part(key=KEY, upload_id=upload_id, part_number=number, data=data)
    else:
        assert isinstance(storage, S3ObjectStorage)
        etag = storage.client.upload_part(
            Bucket=BUCKET, Key=KEY, UploadId=upload_id, PartNumber=number, Body=data
        )["ETag"]
    return UploadedPart(part_number=number, etag=etag)


def test_multipart_round_trip(storage):
    upload_id = storage.create_multipart(key=KEY, content_type="video/mp4")
    first = put_part(storage, upload_id, 1, b"a" * MIN_PART_SIZE)
    last = put_part(storage, upload_id, 2, b"b" * 1024)

    info = storage.complete_multipart(key=KEY, upload_id=upload_id, parts=[last, first])

    assert info.size == MIN_PART_SIZE + 1024
    assert info.content_type == "video/mp4"
    assert storage.head(key=KEY) == info


def test_list_parts_supports_resume(storage):
    upload_id = storage.create_multipart(key=KEY, content_type="video/mp4")
    put_part(storage, upload_id, 2, b"b" * MIN_PART_SIZE)
    put_part(storage, upload_id, 1, b"a" * MIN_PART_SIZE)

    parts = storage.list_parts(key=KEY, upload_id=upload_id)

    assert [p.part_number for p in parts] == [1, 2]
    assert all(p.size == MIN_PART_SIZE for p in parts)


def test_complete_rejects_a_wrong_etag(storage):
    upload_id = storage.create_multipart(key=KEY, content_type="video/mp4")
    put_part(storage, upload_id, 1, b"a" * 10)
    with pytest.raises(InvalidPart):
        storage.complete_multipart(
            key=KEY, upload_id=upload_id, parts=[UploadedPart(1, '"not-the-etag"')]
        )


def test_complete_rejects_a_small_part_that_is_not_last(storage):
    upload_id = storage.create_multipart(key=KEY, content_type="video/mp4")
    small = put_part(storage, upload_id, 1, b"a" * 1024)
    last = put_part(storage, upload_id, 2, b"b" * 1024)
    with pytest.raises(InvalidPart):
        storage.complete_multipart(key=KEY, upload_id=upload_id, parts=[small, last])


def test_abort_is_idempotent_and_forgets_the_upload(storage):
    upload_id = storage.create_multipart(key=KEY, content_type="video/mp4")
    storage.abort_multipart(key=KEY, upload_id=upload_id)
    storage.abort_multipart(key=KEY, upload_id=upload_id)
    with pytest.raises(UploadNotFound):
        storage.list_parts(key=KEY, upload_id=upload_id)


def test_head_of_missing_object_is_none(storage):
    assert storage.head(key="originals/missing.mp4") is None


@pytest.mark.parametrize("number", [0, 10_001])
def test_presign_rejects_out_of_range_part_numbers(storage, number):
    upload_id = storage.create_multipart(key=KEY, content_type="video/mp4")
    with pytest.raises(InvalidPart):
        storage.presign_part(key=KEY, upload_id=upload_id, part_number=number)


def test_s3_presigned_url_targets_the_regional_bucket_with_sigv4():
    with mock_aws():
        client = make_s3_client(region=REGION)
        client.create_bucket(
            Bucket=BUCKET, CreateBucketConfiguration={"LocationConstraint": REGION}
        )
        s3 = S3ObjectStorage(bucket=BUCKET, client=client)
        upload_id = s3.create_multipart(key=KEY, content_type="video/mp4")

        url = s3.presign_part(key=KEY, upload_id=upload_id, part_number=7, expires_in=900)

    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    assert parsed.netloc == f"{BUCKET}.s3.{REGION}.amazonaws.com"
    assert query["partNumber"] == ["7"]
    assert query["uploadId"] == [upload_id]
    assert query["X-Amz-Algorithm"] == ["AWS4-HMAC-SHA256"]
    assert query["X-Amz-Expires"] == ["900"]


def test_memory_presigned_url_requires_a_known_upload():
    memory = InMemoryObjectStorage()
    with pytest.raises(UploadNotFound):
        memory.presign_part(key=KEY, upload_id="nope", part_number=1)
    upload_id = memory.create_multipart(key=KEY, content_type="video/mp4")
    assert upload_id in memory.presign_part(key=KEY, upload_id=upload_id, part_number=1)


def test_s3_list_parts_follows_pagination():
    class PagedClient:
        def __init__(self):
            self.markers = []

        def list_parts(self, **kwargs):
            self.markers.append(kwargs["PartNumberMarker"])
            if kwargs["PartNumberMarker"] == 0:
                return {
                    "Parts": [{"PartNumber": 1, "ETag": '"a"', "Size": 5}],
                    "IsTruncated": True,
                    "NextPartNumberMarker": 1,
                }
            return {"Parts": [{"PartNumber": 2, "ETag": '"b"', "Size": 5}], "IsTruncated": False}

    client = PagedClient()
    parts = S3ObjectStorage(bucket=BUCKET, client=client).list_parts(key=KEY, upload_id="u")  # type: ignore[arg-type]
    assert [p.part_number for p in parts] == [1, 2]
    assert client.markers == [0, 1]


def test_s3_unexpected_errors_become_storage_errors():
    def denied(*args, **kwargs):
        raise ClientError({"Error": {"Code": "AccessDenied", "Message": "no"}}, "Op")

    class DeniedClient:
        create_multipart_upload = abort_multipart_upload = head_object = staticmethod(denied)

    s3 = S3ObjectStorage(bucket=BUCKET, client=DeniedClient())  # type: ignore[arg-type]
    with pytest.raises(StorageError):
        s3.create_multipart(key=KEY, content_type="video/mp4")
    with pytest.raises(StorageError):
        s3.abort_multipart(key=KEY, upload_id="u")
    with pytest.raises(StorageError):
        s3.head(key=KEY)


@pytest.mark.parametrize(
    "parts", [[], [UploadedPart(1, '"a"'), UploadedPart(1, '"b"')], [UploadedPart(0, '"a"')]]
)
def test_sorted_parts_rejects_bad_lists(parts):
    with pytest.raises(InvalidPart):
        sorted_parts(parts)


def test_factory_uses_memory_in_tests():
    assert isinstance(get_object_storage(), InMemoryObjectStorage)


def test_factory_builds_s3_storage_from_settings():
    get_object_storage.cache_clear()
    with override_settings(OBJECT_STORAGE_BACKEND="s3", AWS_PROFILE=None), mock_aws():
        storage = get_object_storage()
    assert isinstance(storage, S3ObjectStorage)
    assert storage.bucket == BUCKET


def test_factory_rejects_unknown_backend():
    get_object_storage.cache_clear()
    with override_settings(OBJECT_STORAGE_BACKEND="ftp"), pytest.raises(ImproperlyConfigured):
        get_object_storage()
