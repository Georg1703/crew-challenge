from rest_framework import serializers

from apps.crews.api.serializers import MemberOut
from apps.notifications.models import Notification


class TargetRefOut(serializers.Serializer):
    type = serializers.CharField(help_text="A registered target's key: the page that shows it.")
    id = serializers.UUIDField()


class NotificationFactsOut(serializers.Serializer):
    on = serializers.CharField(help_text="The key of what was acted on: entry, comment.")
    emoji = serializers.CharField(required=False)
    text = serializers.CharField(required=False, help_text="The comment's first words.")


class NotificationOut(serializers.Serializer):
    id = serializers.UUIDField()
    kind = serializers.ChoiceField(choices=Notification.Kind.choices)
    actor = MemberOut()
    target = TargetRefOut()
    facts = NotificationFactsOut()
    created_at = serializers.DateTimeField()
    read_at = serializers.DateTimeField(allow_null=True)


class NewsQueryIn(serializers.Serializer):
    before = serializers.DateTimeField(
        required=False, help_text="Rows older than this instant (the last row's created_at)."
    )


class NewsOut(serializers.Serializer):
    results = NotificationOut(many=True, help_text="Latest first.")
    unread = serializers.IntegerField(help_text="All of your unread news, for the badge.")


class PushKeyOut(serializers.Serializer):
    public_key = serializers.CharField(
        allow_blank=True, help_text="The VAPID public key to subscribe with; empty: push is off."
    )


class PushKeysIn(serializers.Serializer):
    p256dh = serializers.CharField(max_length=128)
    auth = serializers.CharField(max_length=64)


class PushSubscribeIn(serializers.Serializer):
    endpoint = serializers.URLField(max_length=2000)
    keys = PushKeysIn()


class PushUnsubscribeIn(serializers.Serializer):
    endpoint = serializers.URLField(max_length=2000)
