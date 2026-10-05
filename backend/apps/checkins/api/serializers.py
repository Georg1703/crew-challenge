from rest_framework import serializers

from apps.challenges.api.serializers import PersonOut
from apps.challenges.models import ICONS, Challenge
from apps.checkins.days import DayState

DAY_STATES = (
    DayState.DONE,
    DayState.PARTIAL,
    DayState.TODO,
    DayState.OPEN,
    DayState.MISSED,
    DayState.NOT_DUE,
    DayState.FUTURE,
    DayState.OUTSIDE,
)


class CheckInIn(serializers.Serializer):
    day = serializers.DateField(
        help_text="Today in the crew's time zone; any other day is refused."
    )
    amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
        allow_null=True,
        default=None,
        help_text="For challenges that record a number: how much to add.",
    )


class DayOut(serializers.Serializer):
    day = serializers.DateField()
    state = serializers.ChoiceField(choices=DAY_STATES)


class ProgressOut(serializers.Serializer):
    kind = serializers.ChoiceField(choices=("days", "amount"))
    done = serializers.FloatField()
    goal = serializers.FloatField()


class TodayChallengeOut(serializers.Serializer):
    """One of my challenges today: what to show on its card and in the ring."""

    id = serializers.UUIDField()
    title = serializers.CharField()
    icon = serializers.ChoiceField(choices=ICONS)
    measure = serializers.ChoiceField(choices=Challenge.Measure.choices)
    unit = serializers.CharField()
    frequency = serializers.ChoiceField(choices=Challenge.Frequency.choices)
    times = serializers.IntegerField(allow_null=True)
    target_scope = serializers.ChoiceField(choices=Challenge.TargetScope.choices)
    target_value = serializers.FloatField(allow_null=True)
    proof_kind = serializers.ChoiceField(choices=Challenge.ProofKind.choices)
    proof_required = serializers.BooleanField()
    end_date = serializers.DateField()
    state = serializers.ChoiceField(choices=DAY_STATES, help_text="Today's state.")
    total = serializers.FloatField(allow_null=True, help_text="Today's total (numbers only).")
    streak = serializers.IntegerField(allow_null=True)
    week = DayOut(many=True, help_text="Monday to Sunday of this week.")
    progress = ProgressOut(allow_null=True, help_text="Toward the week's or the period's goal.")
    settled = serializers.BooleanField(
        allow_null=True, help_text="Today's ring segment: full, empty, or none (null)."
    )


class CrewDayOut(serializers.Serializer):
    member = PersonOut()
    done = serializers.IntegerField()
    needed = serializers.IntegerField()


class TodayOut(serializers.Serializer):
    day = serializers.DateField()
    deadline = serializers.DateTimeField(help_text="When today ends (crew-local midnight).")
    challenges = TodayChallengeOut(many=True)
    crew = CrewDayOut(many=True, help_text="Everyone with something today, in join order.")


class BoardRowOut(serializers.Serializer):
    member = PersonOut()
    states = serializers.ListField(
        child=serializers.ChoiceField(choices=DAY_STATES), help_text="One per day."
    )
    streak = serializers.IntegerField(allow_null=True)


class BoardOut(serializers.Serializer):
    days = serializers.ListField(child=serializers.DateField())
    rows = BoardRowOut(many=True)
