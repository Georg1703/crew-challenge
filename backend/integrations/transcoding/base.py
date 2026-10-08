"""What the app needs from video transcoding, independent of AWS.

A finished upload goes in; HLS renditions (360p and 720p) and poster frames come out under an
output prefix in the same bucket: the master playlist at `<prefix>hls.m3u8`, up to
`POSTER_CAPTURES` frames (one a second from the start) as `<prefix>poster.<number>.jpg`. The app
keeps the one with the most detail (videos often start black). Jobs are polled, never called back.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

RUNNING, DONE, FAILED = "running", "done", "failed"
HLS_PLAYLIST = "hls.m3u8"
POSTER_PREFIX = "poster"
POSTER_CAPTURES = 5  # frames at 0, 1, 2, 3 and 4 seconds; a shorter video gives fewer


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
