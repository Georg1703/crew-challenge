from rest_framework import serializers

from apps.challenges.models import ICONS, Challenge, PeriodKind
from apps.challenges.selectors import PHASES


class PersonOut(serializers.Serializer):
    id = serializers.UUIDField()
    display_name = serializers.CharField()
    avatar_seed = serializers.CharField()


class ChallengeIn(serializers.Serializer):
    """The creator's choices. Combinations are checked in services.clean_shape."""

    title = serializers.CharField(max_length=60)
    rules = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")
    icon = serializers.ChoiceField(choices=ICONS, default="star")
    measure = serializers.ChoiceField(choices=Challenge.Measure.choices)
    unit = serializers.CharField(max_length=20, required=False, allow_blank=True, default="")
    window = serializers.ChoiceField(
        choices=Challenge.Window.choices, help_text="The unit that is judged."
    )
    on_days = serializers.ListField(
        child=serializers.IntegerField(min_value=0, max_value=6),
        required=False,
        default=list,
        max_length=7,
        help_text="Day windows only: the weekdays that count, 0 = Monday ... 6 = Sunday; "
        "empty = every day.",
    )
    need_kind = serializers.ChoiceField(choices=Challenge.NeedKind.choices)
    need_value = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="What each window needs: check-ins (1 for a day), or a total (numbers only).",
    )
    day_min = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        allow_null=True,
        default=None,
        help_text="Numbers counted in check-ins: the least amount for a check-in to count.",
    )
    period_kind = serializers.ChoiceField(
        choices=PeriodKind.choices,
        default=PeriodKind.MONTH,
        help_text="The unit of how long it runs: months, weeks or days.",
    )
    period_length = serializers.IntegerField(
        default=1,
        min_value=1,
        help_text="How many months (1-12), weeks (1-52) or days (1-365) it runs.",
    )
    proof_required = serializers.BooleanField(
        default=False, help_text="A photo or a video with each check-in; false: no proof."
    )
    participant_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        allow_null=True,
        default=None,
        help_text="Who takes part (the creator is always in). Create: default the whole crew. "
        "Edit: leave out to keep the list.",
    )


class ParticipantsIn(serializers.Serializer):
    participant_ids = serializers.ListField(
        child=serializers.UUIDField(), help_text="Who takes part; the creator is always in."
    )


class ParticipantOut(serializers.Serializer):
    member = PersonOut()
    left_on = serializers.DateField(
        allow_null=True, help_text="Last day that counted, when they left during the challenge."
    )


class ChallengeOut(serializers.Serializer):
    id = serializers.UUIDField()
    title = serializers.CharField()
    rules = serializers.CharField()
    icon = serializers.ChoiceField(choices=ICONS)
    measure = serializers.ChoiceField(choices=Challenge.Measure.choices)
    unit = serializers.CharField()
    window = serializers.ChoiceField(choices=Challenge.Window.choices)
    on_days = serializers.ListField(child=serializers.IntegerField())
    need_kind = serializers.ChoiceField(choices=Challenge.NeedKind.choices)
    need_value = serializers.DecimalField(max_digits=10, decimal_places=2, coerce_to_string=False)
    day_min = serializers.DecimalField(
        max_digits=10, decimal_places=2, allow_null=True, coerce_to_string=False
    )
    proof_required = serializers.BooleanField(
        help_text="A photo or a video with each check-in; false: no proof."
    )
    state = serializers.ChoiceField(choices=Challenge.State.choices)
    phase = serializers.ChoiceField(choices=PHASES, allow_null=True)
    period_kind = serializers.ChoiceField(choices=PeriodKind.choices)
    period_length = serializers.IntegerField()
    period_start = serializers.DateField(allow_null=True)
    start_date = serializers.DateField(allow_null=True)
    end_date = serializers.DateField(allow_null=True)
    chosen_by = PersonOut(allow_null=True)
    chosen_at = serializers.DateTimeField(allow_null=True)
    created_by = PersonOut(allow_null=True)
    created_at = serializers.DateTimeField()
    revision = serializers.IntegerField()
    vote_count = serializers.IntegerField()
    voters = PersonOut(many=True)
    my_vote = serializers.BooleanField(help_text="The current member voted for it.")
    participants = ParticipantOut(
        many=True, help_text="Who takes part (and who left), in the order they joined the crew."
    )
    taking_part = serializers.BooleanField(
        help_text="The current member is a participant and has not left."
    )
    mine = serializers.BooleanField(help_text="Proposed by the current member.")


class PoolOut(serializers.Serializer):
    proposals = ChallengeOut(many=True, help_text="Newest first.")
    size = serializers.IntegerField(help_text="Proposals in the pool.")
    limit = serializers.IntegerField(help_text="How many the pool can hold (Crew.max_proposals).")


class ScheduleIn(serializers.Serializer):
    period_start = serializers.DateField(
        help_text="First day of the period: the 1st for months, a Monday for weeks, any day from "
        "tomorrow for days. Its length comes from the challenge."
    )
