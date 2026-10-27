"""News for a member: someone reacted to, commented on or answered something of theirs. Any app
posts it (`services.notify`) about any registered target; Web Push is one more way a row reaches
its person (`tasks.push`). Plan: `docs/plans/notifications.md`.
"""

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

from apps.core.models import TimeStampedModel
from apps.crews.models import CrewScopedModel, Member

SNIPPET = 80  # characters of a comment kept in a notification's facts


class Notification(CrewScopedModel):
    """One line of news for one member. Points at the row that caused it (`source`: a reaction, a
    comment) and at the page that shows it (`target`: a journal card). `facts` is frozen when
    posted: the emoji, the comment's first words; who did it is read live.

    A generic key has no database foreign key: every source model declares a `GenericRelation`
    to this model, so a reaction taken back or replaced takes its news with it. A soft-deleted
    source calls `services.retract` instead.
    """

    class Kind(models.TextChoices):
        REACTION = "reaction", "Reacted to something of yours"
        COMMENT = "comment", "Commented on a card of yours, or one you commented on"
        REPLY = "reply", "Answered your comment"

    recipient = models.ForeignKey(Member, on_delete=models.CASCADE, related_name="notifications")
    actor = models.ForeignKey(Member, on_delete=models.CASCADE, related_name="+")
    kind = models.CharField(max_length=16, choices=Kind.choices)
    source_type = models.ForeignKey(ContentType, on_delete=models.PROTECT, related_name="+")
    source_id = models.UUIDField()
    source = GenericForeignKey("source_type", "source_id")
    target_type = models.ForeignKey(ContentType, on_delete=models.PROTECT, related_name="+")
    target_id = models.UUIDField()
    target = GenericForeignKey("target_type", "target_id")
    facts = models.JSONField(default=dict, help_text="What it says, frozen when posted.")
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at", "-id")
        constraints = [
            models.UniqueConstraint(
                fields=["recipient", "source_type", "source_id"], name="notification_once"
            )
        ]
        indexes = [models.Index(fields=["recipient", "-created_at"], name="notification_page")]

    def __str__(self) -> str:
        return f"{self.kind} for {self.recipient} by {self.actor}"


class PushSubscription(TimeStampedModel):
    """One browser (a device) that asked for push notifications, for one user: whatever crew
    they have open, their news reaches it. Dropped when the push service says it is gone."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="push_subscriptions"
    )
    endpoint = models.TextField(unique=True, help_text="The push service URL of the browser.")
    p256dh = models.CharField(max_length=128)
    auth = models.CharField(max_length=64)
    user_agent = models.CharField(max_length=200, blank=True)

    def __str__(self) -> str:
        return f"{self.user}: {self.user_agent or self.endpoint[:40]}"
