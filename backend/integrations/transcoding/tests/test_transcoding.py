"""Tests for the transcoding interface. Tests never call AWS: MediaConvert gets a fake client."""

import pytest
from botocore.exceptions import ClientError
from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings

from integrations.transcoding import (
    DONE,
    FAILED,
    RUNNING,
    InMemoryTranscoder,
    MediaConvertTranscoder,
    TranscodeError,
    get_transcoder,
)
from integrations.transcoding.mediaconvert import job_settings


class FakeMediaConvert:
    """Answers like the boto3 client; `status` is what get_job reports."""

    def __init__(self, status="PROGRESSING", error=None):
        self.status, self.error, self.created = status, error, []

    def create_job(self, **kwargs):
        if self.error:
            raise self.error
        self.created.append(kwargs)
        return {"Job": {"Id": "job-1"}}

    def get_job(self, Id):
        return {"Job": {"Id": Id, "Status": self.status, "ErrorMessage": "Bad input"}}


def test_in_memory_jobs_run_until_finished():
    transcoder = InMemoryTranscoder()
    ok, broken = (transcoder.start(input_key="a.mp4", output_prefix="a/") for _ in range(2))
    assert transcoder.check(job_id=ok).state == RUNNING

    transcoder.finish(ok)
    transcoder.finish(broken, error="Unsupported codec")

    assert transcoder.check(job_id=ok).state == DONE
    assert transcoder.check(job_id=broken).error == "Unsupported codec"
    with pytest.raises(TranscodeError):
        transcoder.check(job_id="nope")


def test_job_settings_write_hls_and_a_poster_next_to_the_original():
    settings = job_settings(input_url="s3://b/v/original.mp4", output_url="s3://b/v/original/")

    assert settings["Inputs"][0]["FileInput"] == "s3://b/v/original.mp4"
    assert settings["Inputs"][0]["VideoSelector"]["Rotate"] == "AUTO"
    hls, poster = settings["OutputGroups"]
    assert hls["OutputGroupSettings"]["HlsGroupSettings"]["Destination"] == "s3://b/v/original/hls"
    assert [o["NameModifier"] for o in hls["Outputs"]] == ["_360p", "_720p"]
    assert {o["VideoDescription"]["ScalingBehavior"] for o in hls["Outputs"]} == {"FIT_NO_UPSCALE"}
    assert poster["OutputGroupSettings"]["FileGroupSettings"]["Destination"] == (
        "s3://b/v/original/poster"
    )
    capture = poster["Outputs"][0]["VideoDescription"]["CodecSettings"]["FrameCaptureSettings"]
    assert (capture["FramerateNumerator"], capture["MaxCaptures"]) == (1, 5)  # 0..4 s


@pytest.mark.parametrize(
    ("status", "state"),
    [("SUBMITTED", RUNNING), ("PROGRESSING", RUNNING), ("COMPLETE", DONE), ("ERROR", FAILED)],
)
def test_mediaconvert_reports_job_states(status, state):
    client = FakeMediaConvert(status=status)
    transcoder = MediaConvertTranscoder(client=client, bucket="b", role_arn="arn:role")

    assert transcoder.start(input_key="v/original.mp4", output_prefix="v/original/") == "job-1"
    assert client.created[0]["Role"] == "arn:role"
    job = transcoder.check(job_id="job-1")
    assert job.state == state
    assert job.error == ("Bad input" if state == FAILED else "")


def test_mediaconvert_errors_become_transcode_errors():
    refused = ClientError({"Error": {"Code": "BadRequestException"}}, "CreateJob")
    transcoder = MediaConvertTranscoder(
        client=FakeMediaConvert(error=refused), bucket="b", role_arn="arn:role"
    )
    with pytest.raises(TranscodeError):
        transcoder.start(input_key="v.mp4", output_prefix="v/")


def test_factory_follows_settings(monkeypatch):
    monkeypatch.delenv("AWS_PROFILE", raising=False)
    for backend, expected in (("off", type(None)), ("mediaconvert", MediaConvertTranscoder)):
        get_transcoder.cache_clear()
        with override_settings(TRANSCODER_BACKEND=backend, MEDIACONVERT_ROLE_ARN="arn:role"):
            assert isinstance(get_transcoder(), expected)
    for backend, role in (("mediaconvert", ""), ("ffmpeg", "arn:role")):
        get_transcoder.cache_clear()
        with (
            override_settings(TRANSCODER_BACKEND=backend, MEDIACONVERT_ROLE_ARN=role),
            pytest.raises(ImproperlyConfigured),
        ):
            get_transcoder()
