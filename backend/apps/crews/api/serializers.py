from rest_framework import serializers

from apps.accounts.models import User
from apps.accounts.services import USERNAME_MAX
from apps.crews.services import DISPLAY_NAME_MAX


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


class MembershipOut(serializers.Serializer):
    crew_id = serializers.UUIDField()
    crew_name = serializers.CharField(source="crew.name")
    display_name = serializers.CharField()
    role = serializers.CharField()


class MeOut(serializers.Serializer):
    user = UserOut()
    member = MemberOut(allow_null=True)
    crew = CrewOut(allow_null=True)
    crews = MembershipOut(many=True, help_text="Every crew the user belongs to, by name.")


class ActiveCrewIn(serializers.Serializer):
    crew_id = serializers.UUIDField()


class MePatchIn(serializers.Serializer):
    display_name = serializers.CharField(max_length=DISPLAY_NAME_MAX, required=False)
    preferred_language = serializers.ChoiceField(choices=User.Language.choices, required=False)


class RotationIn(serializers.Serializer):
    member_ids = serializers.ListField(child=serializers.UUIDField(), min_length=1, max_length=100)


class InviteOut(serializers.Serializer):
    code = serializers.CharField()
    url = serializers.URLField()
    expires_at = serializers.DateTimeField()


class MemberSummaryOut(serializers.Serializer):
    display_name = serializers.CharField()
    avatar_seed = serializers.CharField()


class PendingInviteOut(InviteOut):
    id = serializers.UUIDField()
    created_by = MemberSummaryOut(allow_null=True)


class InvitePreviewOut(serializers.Serializer):
    crew_name = serializers.CharField()
    status = serializers.ChoiceField(choices=["valid", "expired", "used"])
    expires_at = serializers.DateTimeField()
    invited_by = MemberSummaryOut(
        allow_null=True, help_text="Who created the invite. Only for valid invites."
    )
    members = MemberSummaryOut(
        many=True, help_text="Members in rotation order. Empty unless the invite is valid."
    )
    already_member = serializers.BooleanField(
        help_text="True when the logged-in user is already in this crew."
    )
    crew_id = serializers.UUIDField(
        allow_null=True, help_text="The crew's id, only for its own members (to switch to it)."
    )


class JoinWithAccountIn(serializers.Serializer):
    display_name = serializers.CharField(max_length=DISPLAY_NAME_MAX)


class AcceptInviteIn(serializers.Serializer):
    username = serializers.CharField(max_length=USERNAME_MAX)
    password = serializers.CharField(max_length=128, trim_whitespace=False, write_only=True)
    display_name = serializers.CharField(max_length=DISPLAY_NAME_MAX)
    preferred_language = serializers.ChoiceField(
        choices=User.Language.choices, required=False, help_text="The language used to sign up."
    )
