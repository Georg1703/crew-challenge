"""The crew's journal, stored: one card per post, written once and never edited.

The apps that make posts write the cards (check-ins, the Wheel of Doom); this store knows none of
them: a card points at its subject by a generic key, like proofs and reactions do. What the card
said when it was posted is frozen in `facts`; who people are and the media are read live.
"""

from __future__ import annotations

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

from apps.challenges.models import Challenge
from apps.crews.models import CrewScopedModel, Member


class JournalEntry(CrewScopedModel):
    """One card in the crew's journal: a post (a check-in, a "+N", photos added later), a spin
    drawn or served, or the whole crew's finished day. Added or deleted, never edited."""

    class Kind(models.TextChoices):
        CHECK_IN = "check_in", "A check-in post"
        SPIN = "spin", "A spin drawn"
        SERVED = "served", "A punishment served"
        CREW_DAY = "crew_day", "The whole crew finished the day"

    kind = models.CharField(max_length=16, choices=Kind.choices)
    subject_type = models.ForeignKey(ContentType, on_delete=models.PROTECT, related_name="+")
    subject_id = models.UUIDField()
    subject = GenericForeignKey("subject_type", "subject_id")
    member = models.ForeignKey(
        Member,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="+",
        help_text="Who did it; empty for the crew's day.",
    )
    challenge = models.ForeignKey(
        Challenge,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="+",
        help_text="Who may see it: the challenge's people; empty: the whole crew.",
    )
    day = models.DateField(help_text="The crew-local day it sits under.")
    facts = models.JSONField(default=dict, help_text="What the card says, frozen when posted.")

    class Meta:
        ordering = ("-created_at", "-id")  # when it was posted: its place, latest first
        constraints = [
            models.UniqueConstraint(
                fields=["kind", "subject_type", "subject_id", "day"], name="journal_entry_once"
            )
        ]
        indexes = [models.Index(fields=["crew", "-created_at", "-id"], name="journal_page")]

    def __str__(self) -> str:
        return f"{self.kind} {self.day}"
