"""Transcoder on AWS Elemental MediaConvert. The only module that talks to MediaConvert.

The job settings live here as code (not a console job template), so they are reviewed and
versioned with the app. MediaConvert reads the original and writes next to it in the same bucket,
with the role in MEDIACONVERT_ROLE_ARN (see infra/aws/).
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from .base import (
    DONE,
    FAILED,
    HLS_PLAYLIST,
    POSTER_PREFIX,
    RUNNING,
    Job,
    TranscodeError,
    Transcoder,
)

# (name modifier, longest side in pixels, max bitrate): 360p and 720p in portrait or landscape.
RENDITIONS = (("_360p", 640, 1_000_000), ("_720p", 1280, 3_000_000))


def make_mediaconvert_client(*, region: str, profile: str | None = None) -> Any:
    """Regional endpoint: account-specific endpoints (DescribeEndpoints) are no longer needed."""
    return boto3.Session(profile_name=profile, region_name=region).client("mediaconvert")


def _rendition(name: str, side: int, max_bitrate: int) -> dict[str, Any]:
    return {
        "NameModifier": name,
        "ContainerSettings": {"Container": "M3U8", "M3u8Settings": {}},
        "VideoDescription": {
            # A side x side box: shrinks to fit (long side = `side`), never pads, never upscales.
            "Width": side,
            "Height": side,
            "ScalingBehavior": "FIT_NO_UPSCALE",
            "CodecSettings": {
                "Codec": "H_264",
                "H264Settings": {
                    "RateControlMode": "QVBR",
                    "QvbrSettings": {"QvbrQualityLevel": 7},
                    "MaxBitrate": max_bitrate,
                    "QualityTuningLevel": "SINGLE_PASS_HQ",
                    "SceneChangeDetect": "TRANSITION_DETECTION",
                },
            },
        },
        "AudioDescriptions": [
            {
                "AudioSourceName": "Audio Selector 1",
                "CodecSettings": {
                    "Codec": "AAC",
                    "AacSettings": {
                        "Bitrate": 96_000,
                        "CodingMode": "CODING_MODE_2_0",
                        "SampleRate": 48_000,
                    },
                },
            }
        ],
        "OutputSettings": {"HlsSettings": {}},
    }


def job_settings(*, input_url: str, output_url: str) -> dict[str, Any]:
    """HLS (360p + 720p, 6 s segments) and one JPEG poster from the first second."""
    return {
        "TimecodeConfig": {"Source": "ZEROBASED"},
        "Inputs": [
            {
                "FileInput": input_url,
                "TimecodeSource": "ZEROBASED",
                "VideoSelector": {"Rotate": "AUTO"},  # phones store portrait as rotation metadata
                "AudioSelectors": {"Audio Selector 1": {"DefaultSelection": "DEFAULT"}},
            }
        ],
        "OutputGroups": [
            {
                "Name": "HLS",
                "OutputGroupSettings": {
                    "Type": "HLS_GROUP_SETTINGS",
                    "HlsGroupSettings": {
                        "Destination": output_url + HLS_PLAYLIST.removesuffix(".m3u8"),
                        "SegmentLength": 6,
                        "MinSegmentLength": 0,
                        "SegmentControl": "SEGMENTED_FILES",
                        "DirectoryStructure": "SINGLE_DIRECTORY",
                        "ManifestDurationFormat": "INTEGER",
                        "StreamInfResolution": "INCLUDE",
                        "CodecSpecification": "RFC_4281",
                    },
                },
                "Outputs": [_rendition(*r) for r in RENDITIONS],
            },
            {
                "Name": "Poster",
                "OutputGroupSettings": {
                    "Type": "FILE_GROUP_SETTINGS",
                    "FileGroupSettings": {"Destination": output_url + POSTER_PREFIX},
                },
                "Outputs": [
                    {
                        "ContainerSettings": {"Container": "RAW"},
                        "VideoDescription": {
                            "Width": 1280,
                            "Height": 1280,
                            "ScalingBehavior": "FIT_NO_UPSCALE",
                            "CodecSettings": {
                                "Codec": "FRAME_CAPTURE",
                                "FrameCaptureSettings": {
                                    "FramerateNumerator": 1,
                                    "FramerateDenominator": 1,
                                    "MaxCaptures": 1,
                                    "Quality": 80,
                                },
                            },
                        },
                    }
                ],
            },
        ],
    }


class MediaConvertTranscoder(Transcoder):
    def __init__(self, *, client: Any, bucket: str, role_arn: str) -> None:
        self.client = client
        self.bucket = bucket
        self.role_arn = role_arn

    def start(self, *, input_key: str, output_prefix: str) -> str:
        settings = job_settings(
            input_url=f"s3://{self.bucket}/{input_key}",
            output_url=f"s3://{self.bucket}/{output_prefix}",
        )
        with _translate_errors():
            response = self.client.create_job(Role=self.role_arn, Settings=settings)
        return str(response["Job"]["Id"])

    def check(self, *, job_id: str) -> Job:
        with _translate_errors():
            job = self.client.get_job(Id=job_id)["Job"]
        status = job["Status"]  # SUBMITTED, PROGRESSING, COMPLETE, CANCELED or ERROR
        if status == "COMPLETE":
            return Job(state=DONE)
        if status in {"ERROR", "CANCELED"}:
            return Job(state=FAILED, error=str(job.get("ErrorMessage") or status))
        return Job(state=RUNNING)


@contextmanager
def _translate_errors() -> Iterator[None]:
    try:
        yield
    except (BotoCoreError, ClientError) as exc:
        raise TranscodeError(str(exc)) from exc
