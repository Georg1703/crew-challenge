from rest_framework import serializers

from apps.accounts.models import User


class UserOut(serializers.Serializer):
    id = serializers.UUIDField()
    username = serializers.CharField()
    preferred_language = serializers.ChoiceField(choices=User.Language.choices)


class MemberOut(serializers.Serializer):
    id = serializers.UUIDField()
    display_name = serializers.CharField()
    role = serializers.CharField()
    rotation_position = serializers.IntegerField()
    avatar_seed = serializers.CharField()


class CrewOut(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    timezone = serializers.CharField()
    proposal_deadline_day = serializers.IntegerField()
    reveal_time = serializers.TimeField()


class CrewDetailOut(CrewOut):
    members = MemberOut(many=True, help_text="In rotation order.")


class MeOut(serializers.Serializer):
    user = UserOut()
    member = MemberOut(allow_null=True)
    crew = CrewOut(allow_null=True)


class MePatchIn(serializers.Serializer):
    display_name = serializers.CharField(max_length=60, required=False)
    preferred_language = serializers.ChoiceField(choices=User.Language.choices, required=False)


class RotationIn(serializers.Serializer):
    member_ids = serializers.ListField(child=serializers.UUIDField(), min_length=1, max_length=100)


class InviteOut(serializers.Serializer):
    code = serializers.CharField()
    url = serializers.URLField()
    expires_at = serializers.DateTimeField()


class InvitePreviewOut(serializers.Serializer):
    crew_name = serializers.CharField()
    status = serializers.ChoiceField(choices=["valid", "expired", "used"])
    expires_at = serializers.DateTimeField()


class AcceptInviteIn(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(max_length=128, trim_whitespace=False, write_only=True)
    display_name = serializers.CharField(max_length=60)
