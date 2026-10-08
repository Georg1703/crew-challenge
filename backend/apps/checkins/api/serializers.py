from rest_framework import serializers

from apps.challenges.api.serializers import PersonOut
from apps.challenges.models import ICONS, Challenge
from apps.checkins.days import DayState, Verdict
from apps.checkins.models import CheckIn, Proof
from apps.media.models import Upload
from apps.reactions.api.serializers import ReactionSummaryOut

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


class ProofOut(serializers.Serializer):
    id = serializers.UUIDField()
    kind = serializers.ChoiceField(choices=Proof.Kind.choices)
    status = serializers.ChoiceField(choices=Proof.Status.choices)
    url = serializers.CharField(allow_null=True, help_text="The file, once fully uploaded.")
    hls_url = serializers.CharField(
        allow_null=True,
        help_text="A video's HLS playlist once transcoded (production only); else play `url`.",
    )
    thumb_url = serializers.CharField(
        allow_null=True,
        help_text="A video's poster once ready, else a small JPEG from the phone; else show `url`.",
    )
    phone_thumb_url = serializers.CharField(
        allow_null=True,
        help_text="The phone's own small JPEG, if it made one: show it when `thumb_url` fails.",
    )
    created_at = serializers.DateTimeField()
    duration = serializers.IntegerField(
        allow_null=True, help_text="A video's length in seconds, when the phone could read it."
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


class ProofStartIn(serializers.Serializer):
    kind = serializers.ChoiceField(choices=Proof.Kind.choices)
    duration = serializers.IntegerField(
        required=False,
        allow_null=True,
        default=None,
        help_text="A video's length in whole seconds, from the file's metadata.",
    )
    content_type = serializers.CharField(
        max_length=100, help_text="The file's type, e.g. video/mp4."
    )
    size = serializers.IntegerField(min_value=1, help_text="Bytes.")
    fingerprint = serializers.CharField(
        max_length=300,
        required=False,
        default="",
        allow_blank=True,
        help_text="name|size|lastModified of the picked video, to resume it later.",
    )
    thumb_size = serializers.IntegerField(
        min_value=1,
        required=False,
        allow_null=True,
        default=None,
        help_text="Bytes of the JPEG thumbnail made on the phone, if any.",
    )


class PartOut(serializers.Serializer):
    number = serializers.IntegerField()
    etag = serializers.CharField()


class ProofUploadOut(serializers.Serializer):
    """A proof being uploaded and how to send its files straight to storage."""

    proof = ProofOut()
    challenge_id = serializers.UUIDField()
    day = serializers.DateField()
    mode = serializers.ChoiceField(choices=Upload.Mode.choices)
    content_type = serializers.CharField(help_text="Send this Content-Type with the original.")
    put_url = serializers.CharField(
        allow_null=True, help_text="Single mode (photos): PUT the whole file here."
    )
    part_size = serializers.IntegerField(
        allow_null=True, help_text="Multipart (videos): bytes per part; the last one is smaller."
    )
    part_count = serializers.IntegerField(allow_null=True)
    parts = PartOut(many=True, help_text="Parts already uploaded: skip them when resuming.")
    thumb_put_url = serializers.CharField(
        allow_null=True, help_text="PUT the thumbnail here, Content-Type image/jpeg."
    )


class PartsIn(serializers.Serializer):
    numbers = serializers.ListField(
        child=serializers.IntegerField(min_value=1), allow_empty=False, max_length=1000
    )


class PartUrlOut(serializers.Serializer):
    number = serializers.IntegerField()
    url = serializers.CharField()


class PartsOut(serializers.Serializer):
    parts = PartUrlOut(many=True)


class PartIn(serializers.Serializer):
    etag = serializers.CharField(max_length=100, help_text="The ETag header S3 answered with.")


class DaySheetRowOut(serializers.Serializer):
    member = PersonOut()
    state = serializers.ChoiceField(choices=DAY_STATES)
    total = serializers.FloatField(allow_null=True, help_text="The day's total (numbers only).")
    proofs = ProofOut(many=True, help_text="Processing and ready proofs.")


class DaySummaryOut(serializers.Serializer):
    check_ins = serializers.IntegerField()
    proofs = serializers.IntegerField(help_text="Processing and ready proofs.")
    crew_done = serializers.BooleanField(
        help_text="Everyone finished everything due that day (challenges judged day by day)."
    )


class MilestoneOut(serializers.Serializer):
    kind = serializers.ChoiceField(choices=["streak"])
    n = serializers.IntegerField(help_text="Days in a row: 3, 7, 14 or 30.")


class FeedItemOut(serializers.Serializer):
    """One check-in: who, on what, which day, and its proofs."""

    id = serializers.UUIDField(help_text="The check-in.")
    member = PersonOut()
    challenge = ChallengeBriefOut()
    day = serializers.DateField()
    status = serializers.ChoiceField(choices=CheckIn.Status.choices)
    total = serializers.FloatField(allow_null=True, help_text="The day's total (numbers only).")
    activity_at = serializers.DateTimeField(
        help_text="The later of the check-in's last change and its newest proof; the feed's order."
    )
    proofs = ProofOut(many=True, help_text="Processing and ready proofs.")
    streak = serializers.IntegerField(
        allow_null=True, help_text="Days (or weeks) in a row as of this day; null without one."
    )
    day_index = serializers.IntegerField(help_text="This day within the challenge, from 1.")
    day_count = serializers.IntegerField(help_text="Days the challenge runs.")
    week = DayOut(many=True, help_text="The seven days ending on this day.")
    last_amount = serializers.FloatField(
        allow_null=True, help_text="The last amount added (numbers only)."
    )
    target = serializers.FloatField(
        allow_null=True, help_text="The least amount a check-in needs (day_min), if there is one."
    )
    milestone = MilestoneOut(
        allow_null=True, help_text="Set when this check-in made the streak reach 3, 7, 14 or 30."
    )
    day_summary = DaySummaryOut(
        help_text="The crew's whole day (the same on every item of that day), for its divider."
    )
    reactions = ReactionSummaryOut(
        help_text="Reactions; only single cards (a proof, a number or a milestone) take new ones."
    )


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
