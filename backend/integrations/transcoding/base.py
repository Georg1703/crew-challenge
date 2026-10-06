"""What the app needs from video transcoding, independent of AWS.

A finished upload goes in; HLS renditions (360p and 720p) and one poster frame come out under an
output prefix in the same bucket: the master playlist at `<prefix>hls.m3u8`, the poster as
`<prefix>poster.<number>.jpg`. Jobs are polled, never called back.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

RUNNING, DONE, FAILED = "running", "done", "failed"
HLS_PLAYLIST = "hls.m3u8"
POSTER_PREFIX = "poster"


class TranscodeError(Exception):
    """The service failed or refused the request."""


@dataclass(frozen=True, slots=True)
class Job:
    state: str  # RUNNING, DONE or FAILED
    error: str = ""


class Transcoder(ABC):
    @abstractmethod
    def start(self, *, input_key: str, output_prefix: str) -> str:
        """Start a job for a stored video and return its id."""

    @abstractmethod
    def check(self, *, job_id: str) -> Job:
        """Where a job stands."""
