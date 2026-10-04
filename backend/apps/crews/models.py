"""Crews: a group of people who challenge each other, their members, and invite links.

Business rules live in services.py; this module holds data and database-level invariants.
"""

from __future__ import annotations

from datetime import time

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models.functions import Lower

from apps.core import clock
from apps.core.models import TimeStampedModel


def validate_timezone(value: str) -> None:
    try:
        clock.zone(value)
    except clock.UnknownTimezone as exc:
        raise ValidationError(f"{value!r} is not a known time zone.") from exc


def default_timezone() -> str:
    return str(settings.DEFAULT_CREW_TIMEZONE)


class Crew(TimeStampedModel):
    name = models.CharField(max_length=60)
    timezone = models.CharField(
        max_length=64,
        default=default_timezone,
        validators=[validate_timezone],
        help_text="IANA time zone, for example Europe/Chisinau. Challenge days follow it.",
    )
    proposal_deadline_day = models.PositiveSmallIntegerField(
        default=28,
        validators=[MinValueValidator(1), MaxValueValidator(28)],
        help_text="Day of the month by which the proposer must publish the next challenge.",
    )
    reveal_time = models.TimeField(
        default=time(20, 0),
        help_text="Local time on the last day of the month when the next challenge is revealed.",
    )

    class Meta:
        ordering = ("name",)
        constraints = [
            models.CheckConstraint(
                condition=models.Q(proposal_deadline_day__gte=1, proposal_deadline_day__lte=28),
                name="crew_deadline_day_1_to_28",
            ),
        ]

    def __str__(self) -> str:
        return self.name


class CrewScopedQuerySet[M: models.Model](models.QuerySet[M]):
    def for_crew(self, crew: Crew) -> CrewScopedQuerySet[M]:
        return self.filter(crew=crew)


class CrewScopedModel(TimeStampedModel):
    """Base for every row that belongs to a crew. Query with `Model.objects.for_crew(crew)`."""

    crew = models.ForeignKey(Crew, on_delete=models.CASCADE, related_name="%(class)ss")

    objects = CrewScopedQuerySet.as_manager()

    class Meta:
        abstract = True


class Member(CrewScopedModel):
    """A user's membership in one crew. One user can be a member of several crews."""

    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        MEMBER = "member", "Member"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="memberships"
    )
    display_name = models.CharField(max_length=40)
    avatar_seed = models.CharField(max_length=16, help_text="Seed for the generated avatar.")
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.MEMBER)
    rotation_position = models.PositiveSmallIntegerField(
        help_text="Order in which members propose challenges, starting at 0."
    )

    class Meta:
        ordering = ("crew", "rotation_position")
        constraints = [
            models.UniqueConstraint(fields=["crew", "user"], name="member_unique_user_per_crew"),
            # Deferred so a whole rotation can be reordered inside one transaction.
            models.UniqueConstraint(
                fields=["crew", "rotation_position"],
                name="member_unique_rotation_position",
                deferrable=models.Deferrable.DEFERRED,
            ),
            models.UniqueConstraint(
                Lower("display_name"), "crew", name="member_unique_display_name_per_crew"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.display_name} ({self.crew})"

    @property
    def is_admin(self) -> bool:
        return self.role == self.Role.ADMIN


class Invite(CrewScopedModel):
    """A single-use link that lets one new person join a crew."""

    code = models.CharField(max_length=16, unique=True)
    created_by = models.ForeignKey(Member, on_delete=models.CASCADE, related_name="invites_sent")
    expires_at = models.DateTimeField()
    used_by = models.OneToOneField(
        Member, on_delete=models.SET_NULL, null=True, blank=True, related_name="joined_with"
    )
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(used_at__isnull=True, used_by__isnull=True)
                    | models.Q(used_at__isnull=False)
                ),
                name="invite_used_by_requires_used_at",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.code} -> {self.crew}"
