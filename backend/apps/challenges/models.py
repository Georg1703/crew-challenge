"""Challenges: proposals for a period, the crew's votes, the admin's choice, who takes part.

Business rules live in services.py; this module holds data and database-level invariants.
Nothing here assumes a month: rounds and challenges carry explicit dates and a period kind.
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


class Round(CrewScopedModel):
    """Choosing the challenge for one period: members propose and vote, an admin chooses."""

    class State(models.TextChoices):
        OPEN = "open", "Open"
        CLOSED = "closed", "Closed"

    class Selection(models.TextChoices):
        ADMIN = "admin", "An admin chooses"

    period_kind = models.CharField(max_length=10, choices=PeriodKind.choices)
    period_start = models.DateField(help_text="First day of the period, in the crew's time zone.")
    period_end = models.DateField(help_text="Last day of the period, in the crew's time zone.")
    selection = models.CharField(max_length=10, choices=Selection.choices, default=Selection.ADMIN)
    state = models.CharField(max_length=10, choices=State.choices, default=State.OPEN)
    chosen = models.ForeignKey(
        "Challenge", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    chosen_by = models.ForeignKey(
        Member, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    chosen_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("period_start",)
        constraints = [
            models.UniqueConstraint(
                fields=["crew", "period_kind", "period_start"], name="round_unique_period"
            ),
            models.CheckConstraint(
                condition=models.Q(period_end__gte=models.F("period_start")),
                name="round_period_not_reversed",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.crew} {self.period_kind} {self.period_start}"


class Challenge(CrewScopedSoftDeleteModel):
    """A proposal for a round; one per round becomes the chosen challenge."""

    class State(models.TextChoices):
        PROPOSED = "proposed", "Proposed"
        CHOSEN = "chosen", "Chosen"
        NOT_CHOSEN = "not_chosen", "Not chosen"

    class Measure(models.TextChoices):
        CHECK = "check", "Just check in"
        QUANTITY = "quantity", "A number with a unit"
        ABSTAIN = "abstain", "Held it (did not do something)"

    class Frequency(models.TextChoices):
        DAILY = "daily", "Every day"
        WEEKDAYS = "weekdays", "Chosen days of the week"
        TIMES_PER_WEEK = "times_per_week", "A number of times a week"
        TIMES_PER_PERIOD = "times_per_period", "A number of times in the period"
        ONCE = "once", "Once, by the end"

    class TargetScope(models.TextChoices):
        NONE = "none", "No target"
        PER_CHECK_IN = "per_check_in", "Each check-in"
        PER_WEEK = "per_week", "Each week"
        PER_PERIOD = "per_period", "The whole period"

    class ProofKind(models.TextChoices):
        NONE = "none", "No proof"
        PHOTO = "photo", "Photo"
        VIDEO = "video", "Video"
        PHOTO_OR_VIDEO = "photo_or_video", "Photo or video"

    round = models.ForeignKey(Round, on_delete=models.CASCADE, related_name="proposals")
    created_by = models.ForeignKey(
        Member, on_delete=models.SET_NULL, null=True, blank=True, related_name="proposals"
    )
    title = models.CharField(max_length=60)
    rules = models.CharField(max_length=500, blank=True)
    icon = models.CharField(max_length=20, default="star")
    measure = models.CharField(max_length=10, choices=Measure.choices, default=Measure.CHECK)
    unit = models.CharField(max_length=20, blank=True)
    frequency = models.CharField(max_length=20, choices=Frequency.choices, default=Frequency.DAILY)
    weekdays = models.PositiveSmallIntegerField(
        default=0, help_text="Bit mask of chosen days: Monday = 1, Tuesday = 2, ... Sunday = 64."
    )
    times = models.PositiveSmallIntegerField(null=True, blank=True)
    target_scope = models.CharField(
        max_length=20, choices=TargetScope.choices, default=TargetScope.NONE
    )
    target_value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    proof_kind = models.CharField(max_length=20, choices=ProofKind.choices, default=ProofKind.NONE)
    proof_required = models.BooleanField(default=False)
    state = models.CharField(max_length=12, choices=State.choices, default=State.PROPOSED)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    revision = models.PositiveIntegerField(
        default=1, help_text="Goes up with every edit; votes are reset on each edit."
    )

    class Meta(CrewScopedSoftDeleteModel.Meta):
        ordering = ("created_at",)
        constraints = [
            models.CheckConstraint(
                condition=models.Q(state="proposed")
                | models.Q(state="not_chosen")
                | models.Q(start_date__isnull=False, end_date__isnull=False),
                name="challenge_chosen_has_dates",
            ),
        ]

    def __str__(self) -> str:
        return self.title


class Vote(CrewScopedModel):
    """A member's pick in a round. One per member per round; changeable while the round is open."""

    round = models.ForeignKey(Round, on_delete=models.CASCADE, related_name="votes")
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name="votes")
    challenge = models.ForeignKey(Challenge, on_delete=models.CASCADE, related_name="votes")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["round", "member"], name="vote_one_per_member")
        ]

    def __str__(self) -> str:
        return f"{self.member} -> {self.challenge}"


class Participation(CrewScopedModel):
    """A member taking part in a chosen challenge."""

    challenge = models.ForeignKey(
        Challenge, on_delete=models.CASCADE, related_name="participations"
    )
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name="participations")
    joined_on = models.DateField(help_text="First day that counts for this member.")
    ended_on = models.DateField(
        null=True, blank=True, help_text="Last day that counts, when the member left early."
    )

    class Meta:
        ordering = ("joined_on", "created_at")
        constraints = [
            models.UniqueConstraint(
                fields=["challenge", "member"], name="participation_one_per_member"
            )
        ]

    def __str__(self) -> str:
        return f"{self.member} in {self.challenge}"
