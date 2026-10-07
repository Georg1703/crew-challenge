from rest_framework import serializers

from apps.reactions.services import MAX_EMOJI_LENGTH


class ReactionIn(serializers.Serializer):
    emoji = serializers.CharField(max_length=MAX_EMOJI_LENGTH, trim_whitespace=False)


class ReactionGroupOut(serializers.Serializer):
    emoji = serializers.CharField()
    member_ids = serializers.ListField(
        child=serializers.UUIDField(), help_text="Who used it, in the order they did."
    )


class ReactionSummaryOut(serializers.Serializer):
    """A target's reactions. Embedded wherever a reactable thing is shown."""

    groups = ReactionGroupOut(many=True, help_text="In the order each emoji was first used.")
    mine = serializers.CharField(allow_null=True, help_text="Your reaction, if any.")
