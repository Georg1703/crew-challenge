"""Transcoder kept in memory, for tests. Jobs run until a test finishes or fails them."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from .base import DONE, FAILED, RUNNING, Job, TranscodeError, Transcoder


@dataclass
class _Job:
    input_key: str
    output_prefix: str
    state: str = RUNNING
    error: str = ""


class InMemoryTranscoder(Transcoder):
    def __init__(self) -> None:
        self.jobs: dict[str, _Job] = {}

    # --- test helper -------------------------------------------------------------------------
    def finish(self, job_id: str, *, error: str = "") -> None:
        """End a job: done, or failed with `error`."""
        job = self.jobs[job_id]
        job.state, job.error = (FAILED, error) if error else (DONE, "")

    # --- Transcoder --------------------------------------------------------------------------
    def start(self, *, input_key: str, output_prefix: str) -> str:
        job_id = uuid.uuid4().hex
        self.jobs[job_id] = _Job(input_key=input_key, output_prefix=output_prefix)
        return job_id

    def check(self, *, job_id: str) -> Job:
        job = self.jobs.get(job_id)
        if job is None:
            raise TranscodeError(f"No job {job_id!r}.")
        return Job(state=job.state, error=job.error)
