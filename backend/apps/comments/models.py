from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import models

from apps.crews.models import CrewScopedModel, CrewScopedSoftDeleteModel, Member

MAX_LENGTH = 500  # characters


class Comment(CrewScopedSoftDeleteModel):
    """A member's words on a target that takes comments (anything registered in
    `apps.crews.targets` with `comments=True`: a journal card now), or a reply to another comment
    on it (any comment, however long the chain). Never edited; deleting is soft.

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
        help_text="The comment it answers; empty on a comment that answers none.",
    )
    text = models.CharField(max_length=MAX_LENGTH)
    reactions = GenericRelation(
        "reactions.Reaction", content_type_field="target_type", object_id_field="target_id"
    )

    class Meta(CrewScopedSoftDeleteModel.Meta):
        ordering = ("created_at",)
        indexes = [models.Index(fields=["target_type", "target_id", "created_at"])]

    def __str__(self) -> str:
        return f"{self.member}: {self.text[:40]}"


class CommentRead(CrewScopedModel):
    """When a member last saw a target's comments: others' comments after it are unread (and
    never ones from before the member joined the crew)."""

    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name="+")
    target_type = models.ForeignKey(ContentType, on_delete=models.PROTECT, related_name="+")
    target_id = models.UUIDField()
    read_at = models.DateTimeField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["member", "target_type", "target_id"], name="comment_read_once"
            )
        ]

    def __str__(self) -> str:
        return f"{self.member} read {self.target_id} at {self.read_at}"
