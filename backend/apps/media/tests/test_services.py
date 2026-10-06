from datetime import timedelta

import pytest
import time_machine
from django.test import override_settings

from apps.core import clock
from apps.core.errors import ValidationFailed
from apps.media import services
from apps.media.models import GiB, MiB, Transcode, Upload
from integrations.transcoding import get_transcoder
from tests.factories import CrewFactory

pytestmark = pytest.mark.django_db

VIDEO = "crews/c/proofs/p/original.mp4"
PHOTO = "crews/c/proofs/p/original.jpg"


def start(size: int, mode=Upload.Mode.MULTIPART, key=VIDEO, **extra) -> Upload:
    return services.start_upload(
        crew=CrewFactory.create(),
        key=key,
        content_type="image/jpeg" if mode == Upload.Mode.SINGLE else "video/mp4",
        size=size,
        mode=mode,
        expires_at=extra.pop("expires_at", clock.now() + timedelta(days=1)),
        **extra,
    )


def send_part(storage, upload: Upload, number: int, data: bytes) -> str:
    """Play the browser: PUT one part to storage, then report its ETag to the API."""
    etag = storage.upload_part(
        key=upload.key, upload_id=upload.upload_id, part_number=number, data=data
    )
    services.record_part(upload_id=upload.pk, number=number, etag=etag)
    return etag


def test_part_size_grows_with_the_file():
    small, large = Upload(size=GiB - 1), Upload(size=20 * GiB)
    assert (small.part_size, small.part_count) == (16 * MiB, 64)
    assert (large.part_size, large.part_count) == (64 * MiB, 320)


@pytest.mark.parametrize(
    ("size", "mode"),
    [
        (0, Upload.Mode.MULTIPART),
        (20 * GiB + 1, Upload.Mode.MULTIPART),
        (5 * GiB + 1, Upload.Mode.SINGLE),
    ],
)
def test_start_refuses_sizes_out_of_range(size, mode):
    with pytest.raises(ValidationFailed) as error:
        start(size, mode)
    assert "size" in error.value.fields


def test_start_multipart_opens_it_in_storage(object_storage):
    upload = start(20 * GiB, fingerprint="clip.mp4|21474836480|1759600000000")

    assert upload.status == Upload.Status.UPLOADING
    assert upload.upload_id in object_storage.uploads
    assert upload.fingerprint == "clip.mp4|21474836480|1759600000000"


def test_multipart_round_trip(object_storage):
    upload = start(16 * MiB + 10)
    urls = services.sign_parts(upload_id=upload.pk, numbers=[2, 1, 2])
    assert list(urls) == [1, 2]

    send_part(object_storage, upload, 2, b"b" * 10)
    send_part(object_storage, upload, 1, b"a" * 16 * MiB)
    done = services.complete_upload(upload_id=upload.pk)

    assert done.status == Upload.Status.COMPLETE
    assert done.completed_at is not None
    assert object_storage.head(key=VIDEO).size == 16 * MiB + 10
    assert services.complete_upload(upload_id=upload.pk) == done  # a retried request


def test_resume_keeps_the_reported_parts(object_storage):
    upload = start(32 * MiB + 1)
    first = send_part(object_storage, upload, 1, b"a" * 16 * MiB)
    send_part(object_storage, upload, 3, b"c")

    upload.refresh_from_db()
    assert upload.parts == {"1": first, "3": upload.parts["3"]}
    with pytest.raises(services.UploadIncomplete):
        services.complete_upload(upload_id=upload.pk)

    send_part(object_storage, upload, 2, b"b" * 16 * MiB)
    assert services.complete_upload(upload_id=upload.pk).status == Upload.Status.COMPLETE


def test_a_wrong_etag_leaves_the_upload_open(object_storage):
    upload = start(10)
    object_storage.upload_part(key=VIDEO, upload_id=upload.upload_id, part_number=1, data=b"x" * 10)
    services.record_part(upload_id=upload.pk, number=1, etag='"not-what-s3-has"')

    with pytest.raises(services.UploadIncomplete):
        services.complete_upload(upload_id=upload.pk)
    upload.refresh_from_db()
    assert upload.status == Upload.Status.UPLOADING


def test_complete_after_a_lost_answer_finds_the_file(object_storage):
    """S3 assembled the file, but the response never reached us: the retry still succeeds."""
    upload = start(10)
    send_part(object_storage, upload, 1, b"x" * 10)
    parts = object_storage.list_parts(key=VIDEO, upload_id=upload.upload_id)
    object_storage.complete_multipart(key=VIDEO, upload_id=upload.upload_id, parts=parts)

    assert services.complete_upload(upload_id=upload.pk).status == Upload.Status.COMPLETE


@pytest.mark.parametrize("numbers", [[0], [2], []])
def test_part_numbers_stay_in_range(numbers):
    upload = start(10)  # one part
    with pytest.raises(ValidationFailed):
        services.sign_parts(upload_id=upload.pk, numbers=numbers)


@pytest.mark.parametrize("etag", ["", "x" * 101])
def test_a_part_needs_its_etag(etag):
    upload = start(10)
    with pytest.raises(ValidationFailed):
        services.record_part(upload_id=upload.pk, number=1, etag=etag)


def test_single_put_round_trip(object_storage):
    upload = start(4, Upload.Mode.SINGLE, key=PHOTO)
    assert "contentType=image/jpeg" in services.sign_put(upload_id=upload.pk)
    with pytest.raises(services.UploadIncomplete):
        services.complete_upload(upload_id=upload.pk)  # nothing PUT yet

    object_storage.put_object(key=PHOTO, data=b"jpeg", content_type="image/jpeg")

    assert services.complete_upload(upload_id=upload.pk).status == Upload.Status.COMPLETE


def test_modes_do_not_mix():
    single, multi = start(4, Upload.Mode.SINGLE, key=PHOTO), start(10)
    with pytest.raises(ValidationFailed):
        services.sign_parts(upload_id=single.pk, numbers=[1])
    with pytest.raises(ValidationFailed):
        services.sign_put(upload_id=multi.pk)


def test_a_file_of_another_size_is_deleted_and_fails(object_storage):
    upload = start(4, Upload.Mode.SINGLE, key=PHOTO)
    object_storage.put_object(key=PHOTO, data=b"far too big", content_type="image/jpeg")

    with pytest.raises(services.UploadSizeMismatch):
        services.complete_upload(upload_id=upload.pk)

    upload.refresh_from_db()
    assert upload.status == Upload.Status.FAILED  # kept although the request failed
    assert object_storage.head(key=PHOTO) is None
    with pytest.raises(services.UploadClosed):
        services.sign_put(upload_id=upload.pk)


def test_nothing_happens_after_the_deadline(object_storage):
    with time_machine.travel("2026-10-25 20:00Z", tick=False):
        upload = start(10, expires_at=clock.now() + timedelta(hours=4))
        etag = object_storage.upload_part(
            key=VIDEO, upload_id=upload.upload_id, part_number=1, data=b"x" * 10
        )
    with time_machine.travel("2026-10-26 00:00Z", tick=False):
        for call in (
            lambda: services.sign_parts(upload_id=upload.pk, numbers=[1]),
            lambda: services.record_part(upload_id=upload.pk, number=1, etag=etag),
            lambda: services.complete_upload(upload_id=upload.pk),
        ):
            with pytest.raises(services.UploadClosed):
                call()


def test_delete_stops_a_running_upload(object_storage):
    upload = start(10)

    services.delete_upload(upload_id=upload.pk)
    services.delete_upload(upload_id=upload.pk)  # safe twice

    assert upload.upload_id not in object_storage.uploads
    assert Upload.all_objects.get(pk=upload.pk).is_deleted
    with pytest.raises(services.UploadNotFound):
        services.complete_upload(upload_id=upload.pk)


def test_delete_removes_a_finished_file(object_storage):
    upload = start(4, Upload.Mode.SINGLE, key=PHOTO)
    object_storage.put_object(key=PHOTO, data=b"jpeg", content_type="image/jpeg")
    services.complete_upload(upload_id=upload.pk)

    services.delete_upload(upload_id=upload.pk)

    assert object_storage.head(key=PHOTO) is None


def finished_video(storage, key=VIDEO) -> Upload:
    upload = start(10, key=key)
    send_part(storage, upload, 1, b"x" * 10)
    return services.complete_upload(upload_id=upload.pk)


def job_of(upload: Upload) -> Transcode:
    job = services.transcode(upload_id=upload.pk)
    assert job is not None
    return job


def test_one_job_per_video_until_its_renditions_are_made(object_storage, transcoder):
    upload = finished_video(object_storage)
    job = job_of(upload)
    started = transcoder.jobs[job.job_id]
    assert (started.input_key, started.output_prefix) == (VIDEO, "crews/c/proofs/p/original/")
    assert job_of(upload) == job  # checked, not started again
    assert len(transcoder.jobs) == 1

    poster = f"{upload.renditions_prefix}poster.0000000.jpg"
    object_storage.put_object(key=poster, data=b"jpg", content_type="image/jpeg")
    transcoder.finish(job.job_id)
    done = job_of(upload)

    assert (done.status, done.hls_key, done.poster_key) == (
        "done",
        "crews/c/proofs/p/original/hls.m3u8",
        poster,
    )
    assert job_of(upload) == done  # finished: nothing more to ask
    services.delete_upload(upload_id=upload.pk)
    assert object_storage.list_keys(prefix="crews/c/") == []  # the renditions went too


def test_failed_and_stuck_jobs_end(object_storage, transcoder):
    with time_machine.travel("2026-11-10 08:00Z", tick=False):
        broken = finished_video(object_storage, key="crews/c/proofs/1/original.mp4")
        stuck = finished_video(object_storage, key="crews/c/proofs/2/original.mp4")
        broken_job = job_of(broken)
        job_of(stuck)
        transcoder.finish(broken_job.job_id, error="Unsupported codec")

        failed = job_of(broken)
        assert (failed.status, failed.error) == ("failed", "Unsupported codec")
        assert job_of(stuck).status == "running"
    with time_machine.travel("2026-11-10 10:00Z", tick=False):
        given_up = job_of(stuck)
    assert (given_up.status, given_up.error) == ("failed", "Gave up after 2 hours.")


def test_only_finished_videos_are_transcoded_and_only_when_on(object_storage):
    upload = start(10)
    with pytest.raises(services.UploadIncomplete):
        services.transcode(upload_id=upload.pk)

    get_transcoder.cache_clear()
    with override_settings(TRANSCODER_BACKEND="off"):
        assert services.transcode(upload_id=upload.pk) is None
