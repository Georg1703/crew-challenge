from rest_framework import serializers


class MediaSessionOut(serializers.Serializer):
    expires_at = serializers.DateTimeField(
        allow_null=True,
        help_text="Ask again before this. Null when media needs no cookies (local development).",
    )
