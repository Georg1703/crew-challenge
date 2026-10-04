from rest_framework import serializers

from apps.challenges.models import ICONS, Challenge, PeriodKind, Round
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
    frequency = serializers.ChoiceField(choices=Challenge.Frequency.choices)
    weekdays = serializers.ListField(
        child=serializers.IntegerField(min_value=0, max_value=6),
        required=False,
        default=list,
        max_length=7,
        help_text="For frequency=weekdays: 0 = Monday ... 6 = Sunday.",
    )
    times = serializers.IntegerField(required=False, allow_null=True, default=None, min_value=1)
    target_scope = serializers.ChoiceField(
        choices=Challenge.TargetScope.choices, default=Challenge.TargetScope.NONE
    )
    target_value = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, allow_null=True, default=None
    )
    proof_kind = serializers.ChoiceField(
        choices=Challenge.ProofKind.choices, default=Challenge.ProofKind.NONE
    )
    proof_required = serializers.BooleanField(default=False)


class ChallengeOut(serializers.Serializer):
    id = serializers.UUIDField()
    round_id = serializers.UUIDField()
    title = serializers.CharField()
    rules = serializers.CharField()
    icon = serializers.ChoiceField(choices=ICONS)
    measure = serializers.ChoiceField(choices=Challenge.Measure.choices)
    unit = serializers.CharField()
    frequency = serializers.ChoiceField(choices=Challenge.Frequency.choices)
    weekdays = serializers.ListField(child=serializers.IntegerField())
    times = serializers.IntegerField(allow_null=True)
    target_scope = serializers.ChoiceField(choices=Challenge.TargetScope.choices)
    target_value = serializers.DecimalField(
        max_digits=10, decimal_places=2, allow_null=True, coerce_to_string=False
    )
    proof_kind = serializers.ChoiceField(choices=Challenge.ProofKind.choices)
    proof_required = serializers.BooleanField()
    state = serializers.ChoiceField(choices=Challenge.State.choices)
    phase = serializers.ChoiceField(choices=PHASES, allow_null=True)
    start_date = serializers.DateField(allow_null=True)
    end_date = serializers.DateField(allow_null=True)
    created_by = PersonOut(allow_null=True)
    created_at = serializers.DateTimeField()
    revision = serializers.IntegerField()


class ProposalOut(ChallengeOut):
    vote_count = serializers.IntegerField()
    voters = PersonOut(many=True)
    mine = serializers.BooleanField(help_text="Proposed by the current member.")


class RoundOut(serializers.Serializer):
    id = serializers.UUIDField()
    period_kind = serializers.ChoiceField(choices=PeriodKind.choices)
    period_start = serializers.DateField()
    period_end = serializers.DateField()
    state = serializers.ChoiceField(choices=Round.State.choices)
    selection = serializers.ChoiceField(choices=Round.Selection.choices)
    chosen_id = serializers.UUIDField(allow_null=True)
    chosen_by = PersonOut(allow_null=True)
    chosen_at = serializers.DateTimeField(allow_null=True)
    proposals = ProposalOut(many=True, help_text="Oldest first.")
    my_vote = serializers.UUIDField(allow_null=True, help_text="The proposal you voted for.")
    votes_cast = serializers.IntegerField()


class ParticipantOut(serializers.Serializer):
    member = PersonOut()
    joined_on = serializers.DateField()
    ended_on = serializers.DateField(allow_null=True)


class ChallengeDetailOut(ChallengeOut):
    participants = ParticipantOut(many=True)
    taking_part = serializers.BooleanField(help_text="The current member counts in it today.")


class ChallengeRefIn(serializers.Serializer):
    challenge_id = serializers.UUIDField()
