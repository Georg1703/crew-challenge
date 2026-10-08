from datetime import timedelta

import pytest
import time_machine

from apps.core import clock
from apps.media import selectors, services
from apps.media.models import Upload
from apps.media.tests.test_services import VIDEO as KEY
from apps.media.tests.test_services import finished_video, job_of
from tests.factories import CrewFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def video(object_storage, transcoder):
    """A finished video whose renditions are made."""
    upload = finished_video(object_storage)
    poster = f"{upload.renditions_prefix}poster.0000000.jpg"
    object_storage.put_object(key=poster, data=b"j" * 10_000, content_type="image/jpeg")
    transcoder.finish(job_of(upload).job_id)
    job_of(upload)
    return Upload.objects.get(pk=upload.pk)


def test_locally_links_are_presigned_and_videos_play_as_uploaded(video):
    assert str(selectors.url(video)).startswith(f"memory://cc-test-media/{KEY}")
    hls, poster = selectors.renditions(video)
    assert hls is None  # a presigned playlist could not open its segments
    assert str(poster).startswith("memory://cc-test-media/crews/c/proofs/p/original/poster")
    assert selectors.url(None) is None
    assert selectors.renditions(None) == (None, None)
    assert selectors.media_session(crew=video.crew) is None


def test_through_the_cdn_links_are_plain_and_cookies_open_the_crew_folder(cdn, video):
    assert selectors.url(video) == f"https://media.crew.example/{KEY}"
    assert selectors.renditions(video) == (
        "https://media.crew.example/crews/c/proofs/p/original/hls.m3u8",
        "https://media.crew.example/crews/c/proofs/p/original/poster.0000000.jpg",
    )

    with time_machine.travel("2026-11-10 08:00Z", tick=False):
        session = selectors.media_session(crew=video.crew)
        assert session is not None
        assert session.expires_at == clock.now() + timedelta(hours=24)
    assert session.domain == "crew.example"
    assert set(session.cookies) == {
        "CloudFront-Policy",
        "CloudFront-Signature",
        "CloudFront-Key-Pair-Id",
    }


def test_unfinished_files_have_no_link(object_storage):
    upload = services.start_upload(
        crew=CrewFactory.create(),
        key="crews/c/proofs/p/original.jpg",
        content_type="image/jpeg",
        size=4,
        mode=Upload.Mode.SINGLE,
        expires_at=clock.now() + timedelta(days=1),
    )
    assert selectors.url(upload) is None
    assert selectors.renditions(upload) == (None, None)
    assert selectors.transcoding()
