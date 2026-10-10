from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import models

from apps.crews.models import CrewScopedSoftDeleteModel, Member

MAX_LENGTH = 500  # characters
MAX_LEVEL = 5  # a comment is level 1, a reply to it level 2, ...


class Comment(CrewScopedSoftDeleteModel):
    """A member's words on a target that takes comments (anything registered in
    `apps.crews.targets` with `comments=True`: a journal card now), or a reply to another comment
    on it, down to `MAX_LEVEL`. Never edited; deleting is soft.

    A generic key has no database foreign key: every target model that takes comments declares a
    `GenericRelation` to this model, so deleting the target deletes its comments.
    """

    target_type = models.ForeignKey(ContentType, on_delete=models.PROTECT, related_name="+")
    target_id = models.UUIDField()
    target = GenericForeignKey("target_type", "target_id")
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name="comments")
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="replies",
        help_text="The comment it answers; empty on level 1.",
    )
    level = models.PositiveSmallIntegerField(
        default=1, help_text="The parent's level + 1 (stored: a comment never moves)."
    )
    text = models.CharField(max_length=MAX_LENGTH)
    reactions = GenericRelation(
        "reactions.Reaction", content_type_field="target_type", object_id_field="target_id"
    )

    class Meta(CrewScopedSoftDeleteModel.Meta):
        ordering = ("created_at",)
        indexes = [models.Index(fields=["target_type", "target_id", "created_at"])]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(level__gte=1, level__lte=MAX_LEVEL), name="comment_level"
            )
        ]

    def __str__(self) -> str:
        return f"{self.member}: {self.text[:40]}"
