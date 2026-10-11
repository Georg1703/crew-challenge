from rest_framework import serializers

from apps.comments.models import MAX_LENGTH
from apps.reactions.api.serializers import ReactionSummaryOut


class CommentIn(serializers.Serializer):
    text = serializers.CharField(max_length=MAX_LENGTH)
    parent_id = serializers.UUIDField(
        required=False, allow_null=True, help_text="The comment it answers, on the same target."
    )


class CommentOut(serializers.Serializer):
    id = serializers.UUIDField()
    member_id = serializers.UUIDField(help_text="Its writer.")
    parent_id = serializers.UUIDField(allow_null=True, help_text="The comment it answers.")
    text = serializers.CharField()
    created_at = serializers.DateTimeField()
    reactions = ReactionSummaryOut(help_text="Target `comment`, this comment's id.")


class ThreadOut(serializers.Serializer):
    results = CommentOut(many=True, help_text="Oldest first: a reply's parent comes before it.")


class CommentSummaryOut(serializers.Serializer):
    """A target's comments, embedded where the target is shown (a journal card)."""

    count = serializers.IntegerField()
    member_ids = serializers.ListField(
        child=serializers.UUIDField(), help_text="The last writers, latest first, up to 3."
    )
    unread = serializers.IntegerField(help_text="Others' comments you have not seen.")


class UnreadOut(serializers.Serializer):
    count = serializers.IntegerField(
        help_text="Others' unread comments on what you posted or commented on."
    )
