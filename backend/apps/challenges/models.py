"""Challenges: the crew's pool of proposals, votes, the admin's schedule, who takes part.

Business rules live in services.py; this module holds data and database-level invariants.
Nothing here assumes a month: a scheduled challenge carries its period kind and explicit dates.
"""

from __future__ import annotations

from django.db import models

from apps.crews.models import CrewScopedModel, CrewScopedSoftDeleteModel, Member

# Icons a challenge can use (shapes live in the frontend's shared Icon set).
ICONS = (
    "dumbbell",
    "running",
    "book",
    "water",
    "sugar",
    "phone",
    "sleep",
    "walk",
    "meditate",
    "food",
    "money",
    "star",
)


class PeriodKind(models.TextChoices):
    MONTH = "month", "Month"
    WEEK = "week", "Week"
    CUSTOM = "custom", "Custom"


class Challenge(CrewScopedSoftDeleteModel):
    """A proposal in the crew's pool until an admin schedules it for a period (then `chosen`).

    Several challenges can run in the same period.
    """

    class State(models.TextChoices):
        PROPOSED = "proposed", "Proposed"
        CHOSEN = "chosen", "Chosen"

    class Measure(models.TextChoices):
        CHECK = "check", "Just check in"
        QUANTITY = "quantity", "A number with a unit"
        ABSTAIN = "abstain", "Held it (did not do something)"

    class Window(models.TextChoices):
        DAY = "day", "Each day"
        WEEK = "week", "Each week, Monday to Sunday"
        PERIOD = "period", "The whole period"

    class NeedKind(models.TextChoices):
        COUNT = "count", "A number of check-ins"
        AMOUNT = "amount", "A total amount"

    class ProofKind(models.TextChoices):
        NONE = "none", "No proof"
        PHOTO = "photo", "Photo"
        VIDEO = "video", "Video"
        PHOTO_OR_VIDEO = "photo_or_video", "Photo or video"

    created_by = models.ForeignKey(
        Member, on_delete=models.SET_NULL, null=True, blank=True, related_name="proposals"
    )
    title = models.CharField(max_length=60)
    rules = models.CharField(max_length=500, blank=True)
    icon = models.CharField(max_length=20, default="star")
    measure = models.CharField(max_length=10, choices=Measure.choices, default=Measure.CHECK)
    unit = models.CharField(max_length=20, blank=True)
    window = models.CharField(
        max_length=10,
        choices=Window.choices,
        default=Window.DAY,
        help_text="The unit that is judged (apps/challenges/windows.py).",
    )
    on_days = models.PositiveSmallIntegerField(
        default=0,
        help_text="Weekdays that count, as a bit mask (Monday = 1 ... Sunday = 64); 0 = every day.",
    )
    need_kind = models.CharField(max_length=10, choices=NeedKind.choices, default=NeedKind.COUNT)
    need_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=1,
        help_text="What each window needs: a number of check-ins, or a total.",
    )
    day_min = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="The least amount for a day's check-in to count (numbers only).",
    )
    proof_kind = models.CharField(max_length=20, choices=ProofKind.choices, default=ProofKind.NONE)
    proof_required = models.BooleanField(default=False)
    state = models.CharField(max_length=12, choices=State.choices, default=State.PROPOSED)
    period_kind = models.CharField(max_length=10, choices=PeriodKind.choices, blank=True)
    period_start = models.DateField(
        null=True, blank=True, help_text="First day of the period (the 1st for a month)."
    )
    start_date = models.DateField(
        null=True,
        blank=True,
        help_text="First day that counts (after period_start when chosen late).",
    )
    end_date = models.DateField(null=True, blank=True, help_text="Last day of the period.")
    chosen_by = models.ForeignKey(
        Member, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    chosen_at = models.DateTimeField(null=True, blank=True)
    revision = models.PositiveIntegerField(
        default=1, help_text="Goes up with every edit; votes are reset on each edit."
    )

    class Meta(CrewScopedSoftDeleteModel.Meta):
        ordering = ("created_at",)
        indexes = [models.Index(fields=["crew", "state", "start_date"])]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    state="proposed",
                    period_kind="",
                    period_start__isnull=True,
                    start_date__isnull=True,
                    end_date__isnull=True,
                )
                | models.Q(
                    state="chosen",
                    period_start__isnull=False,
                    start_date__gte=models.F("period_start"),
                    end_date__gte=models.F("start_date"),
                )
                & ~models.Q(period_kind=""),
                name="challenge_period_matches_state",
            ),
            models.CheckConstraint(
                condition=models.Q(need_value__gt=0), name="challenge_need_above_zero"
            ),
            models.CheckConstraint(
                condition=models.Q(need_kind="count") | models.Q(measure="quantity"),
                name="challenge_a_total_needs_numbers",
            ),
            models.CheckConstraint(
                condition=models.Q(day_min__isnull=True)
                | models.Q(measure="quantity", need_kind="count"),
                name="challenge_a_day_minimum_needs_counted_numbers",
            ),
            models.CheckConstraint(
                condition=~models.Q(window="day") | models.Q(need_kind="count", need_value=1),
                name="challenge_a_day_needs_one_check_in",
            ),
            models.CheckConstraint(
                condition=models.Q(on_days=0) | models.Q(window="day"),
                name="challenge_chosen_days_only_per_day",
            ),
        ]

    def __str__(self) -> str:
        return self.title


class Vote(CrewScopedModel):
    """A member likes a proposal. A member votes for as many proposals as they want, once each."""

    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name="votes")
    challenge = models.ForeignKey(Challenge, on_delete=models.CASCADE, related_name="votes")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["challenge", "member"], name="vote_one_per_member_and_challenge"
            )
        ]

    def __str__(self) -> str:
        return f"{self.member} -> {self.challenge}"


class Participant(CrewScopedModel):
    """A member the creator selected for a challenge: they see it, vote on it and, once it is
    scheduled, take part in it. Opting out before the start deletes the row; leaving during the
    challenge sets `left_on` (they stop seeing it; the board keeps their days).
    """

    challenge = models.ForeignKey(Challenge, on_delete=models.CASCADE, related_name="participants")
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name="participations")
    left_on = models.DateField(
        null=True, blank=True, help_text="Last day that counts, when the member left during it."
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["challenge", "member"], name="participant_one_per_member"
            )
        ]

    def __str__(self) -> str:
        return f"{self.member} in {self.challenge}"
