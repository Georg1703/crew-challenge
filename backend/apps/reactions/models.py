from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

from apps.crews.models import CrewScopedModel, Member


class Reaction(CrewScopedModel):
    """One member's emoji on one target (a check-in now; anything registered in `targets`).

    A generic key has no database foreign key: every target model declares a `GenericRelation`
    to this model, so deleting the target deletes its reactions (see `targets.py`).
    """

    target_type = models.ForeignKey(ContentType, on_delete=models.PROTECT, related_name="+")
    target_id = models.UUIDField()
    target = GenericForeignKey("target_type", "target_id")
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name="reactions")
    emoji = models.CharField(max_length=32)

    class Meta:
        ordering = ("created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=["target_type", "target_id", "member"], name="reaction_once_per_member"
            )
        ]
        indexes = [models.Index(fields=["target_type", "target_id", "created_at"])]

    def __str__(self) -> str:
        return f"{self.member} {self.emoji}"
