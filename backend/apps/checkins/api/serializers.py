from rest_framework import serializers

from apps.challenges.api.serializers import PersonOut
from apps.challenges.models import ICONS, Challenge
from apps.checkins.days import DayState, Verdict
from apps.checkins.models import NOTE_MAX_LENGTH
from apps.proofs.api.serializers import ProofOut

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
    note = serializers.CharField(
        max_length=NOTE_MAX_LENGTH,
        required=False,
        allow_blank=True,
        help_text="The day's note, with its first post only (the check-in); never edited.",
    )


class DayOut(serializers.Serializer):
    day = serializers.DateField()
    state = serializers.ChoiceField(choices=DAY_STATES)


VERDICTS = (Verdict.MET, Verdict.FAILED, Verdict.OPEN, Verdict.FUTURE)


class WindowOut(serializers.Serializer):
    """A stretch of days judged as one unit, what it asks for, and how it stands."""

    first = serializers.DateField()
    last = serializers.DateField()
    need = serializers.FloatField(help_text="What this window asks for: check-ins, or a total.")
    full_need = serializers.FloatField(
        help_text="What a whole window asks for; more than `need` when this one is cut short."
    )
    done = serializers.FloatField(
        allow_null=True, help_text="Done so far; null for someone who doesn't take part."
    )
    state = serializers.ChoiceField(
        choices=VERDICTS, allow_null=True, help_text="Null for someone who doesn't take part."
    )


class ChallengeBriefOut(serializers.Serializer):
    id = serializers.UUIDField()
    title = serializers.CharField()
    icon = serializers.ChoiceField(choices=ICONS)
    measure = serializers.ChoiceField(choices=Challenge.Measure.choices)
    unit = serializers.CharField()


class TodayChallengeOut(ChallengeBriefOut):
    """One of my challenges today: what to show on its card and in the ring."""

    window = serializers.ChoiceField(choices=Challenge.Window.choices)
    need_kind = serializers.ChoiceField(choices=Challenge.NeedKind.choices)
    need_value = serializers.FloatField()
    day_min = serializers.FloatField(allow_null=True)
    proof_required = serializers.BooleanField(
        help_text="A photo or a video with each check-in; false: no proof."
    )
    end_date = serializers.DateField()
    state = serializers.ChoiceField(choices=DAY_STATES, help_text="Today's state.")
    total = serializers.FloatField(allow_null=True, help_text="Today's total (numbers only).")
    streak = serializers.IntegerField(allow_null=True)
    week = DayOut(many=True, help_text="Monday to Sunday of this week.")
    current = WindowOut(
        allow_null=True,
        help_text="The week, month or period today is in; null for challenges judged day by day.",
    )
    settled = serializers.BooleanField(
        allow_null=True, help_text="Today's ring segment: full, empty, or none (null)."
    )
    proofs = ProofOut(many=True, help_text="Today's proofs, uploads in flight too.")
    proof_days = serializers.ListField(
        child=serializers.DateField(), help_text="Days of this week with proof."
    )


class CrewChallengeOut(serializers.Serializer):
    challenge_id = serializers.UUIDField()
    state = serializers.ChoiceField(
        choices=["done", "started", "todo"], help_text="Started: a number below the day's target."
    )


class CrewDayOut(serializers.Serializer):
    member = PersonOut()
    done = serializers.IntegerField()
    needed = serializers.IntegerField()
    challenges = CrewChallengeOut(many=True, help_text="One per segment of their ring today.")


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
    proof_days = serializers.ListField(
        child=serializers.DateField(), help_text="Days of the month with proof."
    )


class BoardOut(serializers.Serializer):
    days = serializers.ListField(child=serializers.DateField())
    rows = BoardRowOut(many=True)


class DaySheetRowOut(serializers.Serializer):
    member = PersonOut()
    state = serializers.ChoiceField(choices=DAY_STATES)
    total = serializers.FloatField(allow_null=True, help_text="The day's total (numbers only).")
    proofs = ProofOut(many=True, help_text="Processing and ready proofs.")


class MemberChallengeOut(serializers.Serializer):
    challenge = ChallengeBriefOut()
    states = serializers.ListField(
        child=serializers.ChoiceField(choices=DAY_STATES), help_text="One per day of the month."
    )
    proof_days = serializers.ListField(child=serializers.DateField())
    streak = serializers.IntegerField(allow_null=True)
    today = serializers.ChoiceField(choices=DAY_STATES, help_text="Today's state.")


class ProofDayOut(serializers.Serializer):
    day = serializers.DateField()
    challenge = ChallengeBriefOut()
    proofs = ProofOut(many=True)


class MemberProgressOut(serializers.Serializer):
    """A member's month, on the challenges you can see."""

    member = PersonOut()
    days = serializers.ListField(child=serializers.DateField(), help_text="The month's days.")
    streak = serializers.IntegerField(help_text="Their best current streak.")
    longest_streak = serializers.IntegerField()
    month_done = serializers.IntegerField(
        help_text="Due days done this month so far (challenges judged day by day)."
    )
    month_due = serializers.IntegerField(
        help_text="Due days this month so far; today counts once done."
    )
    challenges = MemberChallengeOut(many=True)
    proof_days = ProofDayOut(many=True, help_text="Their proofs this month, latest day first.")
