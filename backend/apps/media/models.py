"""Media: files the browser sends straight to the media bucket (they never pass through Django).

Low level: knows keys, sizes and parts, nothing about challenges or proofs. The caller (a proof)
picks the key, the mode and the deadline. Business rules live in services.py.
"""

from __future__ import annotations

from django.db import models

from apps.crews.models import CrewScopedSoftDeleteModel

MiB = 1024 * 1024
GiB = 1024 * MiB


class Upload(CrewScopedSoftDeleteModel):
    """One file in the media bucket. Deleting it removes the file and keeps the row."""

    class Mode(models.TextChoices):
        SINGLE = "single", "One presigned PUT"
        MULTIPART = "multipart", "Multipart, resumable"

    class Status(models.TextChoices):
        UPLOADING = "uploading", "Uploading"
        COMPLETE = "complete", "Complete"
        FAILED = "failed", "Failed"

    key = models.CharField(max_length=255, unique=True, help_text="Object key, made on the server.")
    content_type = models.CharField(max_length=100)
    size = models.BigIntegerField(help_text="Bytes the browser announced; checked on complete.")
    fingerprint = models.CharField(
        max_length=300, blank=True, help_text="Name, size and lastModified of the file, to resume."
    )
    mode = models.CharField(max_length=10, choices=Mode.choices)
    upload_id = models.CharField(max_length=1024, blank=True, help_text="S3 multipart upload id.")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.UPLOADING)
    parts = models.JSONField(
        default=dict, blank=True, help_text='ETag of each finished part: {"1": "\\"etag\\""}.'
    )
    expires_at = models.DateTimeField(help_text="The upload must complete before this instant.")
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return self.key

    @property
    def part_size(self) -> int:
        """Bytes per part (all but the last): 16 MiB under 1 GiB, 64 MiB above."""
        return 16 * MiB if self.size < GiB else 64 * MiB

    @property
    def part_count(self) -> int:
        return -(-self.size // self.part_size)  # rounded up
