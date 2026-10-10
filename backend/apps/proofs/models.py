"""Proofs: a photo or video backing something a member did (a check-in now, a spin later).

Generic, like reactions: a proof points at its subject by a generic key. The subject's app decides
when a proof may start (its own rules, under a lock on the subject's row) and shows the proofs
through a `GenericRelation`; this app moves the files and knows nothing about the subjects.
Business rules live in services.py.
"""

from __future__ import annotations

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

from apps.crews.models import CrewScopedSoftDeleteModel, Member
from apps.media.models import Upload


class Proof(CrewScopedSoftDeleteModel):
    """A photo or video backing a subject: a draft file until its post publishes it (at most 5 a
    post). A draft can be removed; a posted one goes only with its post."""

    class Kind(models.TextChoices):
        PHOTO = "photo", "Photo"
        VIDEO = "video", "Video"

    class Status(models.TextChoices):
        UPLOADING = "uploading", "Uploading"
        PROCESSING = "processing", "Processing (video renditions)"
        READY = "ready", "Ready"
        FAILED = "failed", "Failed"

    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name="proofs")
    subject_type = models.ForeignKey(ContentType, on_delete=models.PROTECT, related_name="+")
    subject_id = models.UUIDField()
    subject = GenericForeignKey("subject_type", "subject_id")
    kind = models.CharField(max_length=10, choices=Kind.choices)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.UPLOADING)
    original = models.ForeignKey(Upload, on_delete=models.PROTECT, related_name="+")
    thumb = models.ForeignKey(
        Upload,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
        help_text="A small JPEG made on the phone (a video's poster frame).",
    )
    duration = models.PositiveIntegerField(
        null=True, blank=True, help_text="A video's length in seconds, read on the phone."
    )
    post_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="The post that published it (a check-in's entry, a served spin); empty: a draft.",
    )

    class Meta(CrewScopedSoftDeleteModel.Meta):
        db_table = "checkins_proof"  # it moved here from check-ins; the table stayed
        ordering = ("created_at",)
        indexes = [models.Index(fields=["subject_type", "subject_id"], name="proof_subject")]

    def __str__(self) -> str:
        return f"{self.kind} by {self.member_id} for {self.subject_id}"
