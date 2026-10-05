"""Check-ins: what a participant recorded for one challenge on one day.

Missed days are not stored: a due day before today without a `done` check-in is missed
(see days.py). Business rules live in services.py.
"""

from __future__ import annotations

from django.db import models

from apps.challenges.models import Challenge
from apps.crews.models import CrewScopedModel, Member


class CheckIn(CrewScopedModel):
    """One participant, one challenge, one day. Created by the day's first entry."""

    class Status(models.TextChoices):
        DONE = "done", "Done"
        IN_PROGRESS = "in_progress", "In progress (a number below the day's target)"

    challenge = models.ForeignKey(Challenge, on_delete=models.CASCADE, related_name="check_ins")
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name="check_ins")
    day = models.DateField(help_text="The challenge day, in the crew's time zone.")
    status = models.CharField(max_length=12, choices=Status.choices)
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="The day's total for challenges that record a number; empty otherwise.",
    )

    class Meta:
        ordering = ("day", "created_at")
        constraints = [
            models.UniqueConstraint(
                fields=["challenge", "member", "day"], name="check_in_once_per_day"
            )
        ]
        indexes = [models.Index(fields=["challenge", "day"])]

    def __str__(self) -> str:
        return f"{self.member} {self.challenge} {self.day}"


class CheckInEntry(CrewScopedModel):
    """One "+N" (or the single tap of a check-in without a number). Undo removes the last one."""

    check_in = models.ForeignKey(CheckIn, on_delete=models.CASCADE, related_name="entries")
    number = models.PositiveSmallIntegerField(help_text="1, 2, 3... in the order they were added.")
    amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    class Meta:
        ordering = ("number",)
        constraints = [
            models.UniqueConstraint(fields=["check_in", "number"], name="entry_number_once")
        ]

    def __str__(self) -> str:
        return f"{self.check_in}: {self.amount}"
