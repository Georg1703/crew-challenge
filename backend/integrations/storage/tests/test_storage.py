"""Tests for the storage interface, using the in-memory implementation.

The S3 adapter is a thin wrapper around boto3 and is not unit-tested here: it is checked against
the real dev bucket by the upload smoke test. Tests never call AWS.
"""

import pytest
from django.core.exceptions import ImproperlyConfigured
from django.http import Http404
from django.test import RequestFactory, override_settings

from integrations.storage import (
    MIN_PART_SIZE,
    InMemoryObjectStorage,
    InvalidPart,
    S3ObjectStorage,
    StorageError,
    UploadedPart,
    UploadNotFound,
    get_object_storage,
)
from integrations.storage.base import sorted_parts
from integrations.storage.memory_views import memory_bucket

KEY = "originals/crew-1/proof-1.mp4"


@pytest.fixture
def storage() -> InMemoryObjectStorage:
    return InMemoryObjectStorage(bucket="cc-test-media")


def put_part(storage: InMemoryObjectStorage, upload_id: str, number: int, data: bytes):
    """Play the browser: upload one part and return what it reports to the API."""
    etag = storage.upload_part(key=KEY, upload_id=upload_id, part_number=number, data=data)
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
    put_part(storage, upload_id, 2, b"b" * 10)
    put_part(storage, upload_id, 1, b"a" * 10)

    parts = storage.list_parts(key=KEY, upload_id=upload_id)

    assert [p.part_number for p in parts] == [1, 2]
    assert all(p.size == 10 for p in parts)


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


def test_list_and_delete_by_prefix(storage):
    for key in ("v/hls.m3u8", "v/hls_360p_00001.ts", "v2/hls.m3u8"):
        storage.put_object(key=key, data=b"x", content_type="application/octet-stream")

    assert storage.list_keys(prefix="v/") == ["v/hls.m3u8", "v/hls_360p_00001.ts"]
    storage.delete_prefix(prefix="v/")
    storage.delete_prefix(prefix="v/")  # nothing left: still fine

    assert list(storage.objects) == ["v2/hls.m3u8"]


def test_head_of_missing_object_is_none(storage):
    assert storage.head(key="originals/missing.mp4") is None


def test_single_put_round_trip_and_delete(storage):
    key = "originals/crew-1/photo.jpg"
    assert "contentType=image/jpeg" in storage.presign_put(key=key, content_type="image/jpeg")
    storage.put_object(key=key, data=b"jpeg", content_type="image/jpeg")
    assert key in storage.presign_get(key=key)

    info = storage.head(key=key)
    assert info is not None
    assert (info.size, info.content_type) == (4, "image/jpeg")

    storage.delete(key=key)
    storage.delete(key=key)  # safe twice
    assert storage.head(key=key) is None


def test_presign_requires_a_known_upload_and_a_valid_part_number(storage):
    with pytest.raises(UploadNotFound):
        storage.presign_part(key=KEY, upload_id="nope", part_number=1)
    upload_id = storage.create_multipart(key=KEY, content_type="video/mp4")
    assert upload_id in storage.presign_part(key=KEY, upload_id=upload_id, part_number=1)
    for number in (0, 10_001):
        with pytest.raises(InvalidPart):
            storage.presign_part(key=KEY, upload_id=upload_id, part_number=number)


@pytest.mark.parametrize(
    "parts", [[], [UploadedPart(1, '"a"'), UploadedPart(1, '"b"')], [UploadedPart(0, '"a"')]]
)
def test_sorted_parts_rejects_bad_lists(parts):
    with pytest.raises(InvalidPart):
        sorted_parts(parts)


def test_factory_uses_memory_in_tests():
    assert isinstance(get_object_storage(), InMemoryObjectStorage)


def test_factory_builds_s3_storage_from_settings(monkeypatch):
    monkeypatch.delenv("AWS_PROFILE", raising=False)  # building a client must not need a profile
    get_object_storage.cache_clear()
    with override_settings(OBJECT_STORAGE_BACKEND="s3", AWS_PROFILE=None):
        storage = get_object_storage()
    assert isinstance(storage, S3ObjectStorage)
    assert storage.bucket == "cc-test-media"


def test_factory_rejects_unknown_backend():
    get_object_storage.cache_clear()
    with override_settings(OBJECT_STORAGE_BACKEND="ftp"), pytest.raises(ImproperlyConfigured):
        get_object_storage()


def test_put_and_copy_store_files_from_the_server(storage):
    storage.put(key="demo/a.png", data=b"png", content_type="image/png")
    storage.copy(source="demo/a.png", key="demo/b.png")

    info = storage.head(key="demo/b.png")
    assert info is not None
    assert (info.size, info.content_type) == (3, "image/png")
    with pytest.raises(StorageError):
        storage.copy(source="demo/missing.png", key="demo/c.png")


def test_debug_urls_point_at_the_dev_view_which_stands_in_for_s3():
    get_object_storage.cache_clear()
    with override_settings(DEBUG=True):
        storage = get_object_storage()
    assert isinstance(storage, InMemoryObjectStorage)
    assert storage.presign_get(key=KEY).startswith(f"/api/dev-storage/{KEY}?")
    requests = RequestFactory()

    def put(query: str, data: bytes, content_type: str = "video/mp4"):
        request = requests.put(f"/api/dev-storage/{KEY}?{query}", data, content_type=content_type)
        return memory_bucket(request, KEY)

    upload_id = storage.create_multipart(key=KEY, content_type="video/mp4")
    part = put(f"uploadId={upload_id}&partNumber=1", b"part")
    assert part["ETag"] == storage.list_parts(key=KEY, upload_id=upload_id)[0].etag
    assert put("uploadId=nope&partNumber=1", b"part").status_code == 400

    whole = put("contentType=image/jpeg", b"jpg", "image/jpeg")
    assert whole["Location"] == f"http://testserver/api/dev-storage/{KEY}"
    served = memory_bucket(requests.get(f"/api/dev-storage/{KEY}"), KEY)
    assert (served.content, served["Content-Type"]) == (b"jpg", "image/jpeg")
    with pytest.raises(Http404):
        memory_bucket(requests.get("/api/dev-storage/missing"), "missing")
