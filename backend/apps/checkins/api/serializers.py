from rest_framework import serializers

from apps.challenges.api.serializers import PersonOut
from apps.challenges.models import ICONS, Challenge
from apps.checkins.days import DayState
from apps.checkins.models import CheckIn, Proof
from apps.media.models import Upload

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
        help_text="A small JPEG from the phone, or a video's poster; else show `url`.",
    )
    created_at = serializers.DateTimeField()


class ChallengeBriefOut(serializers.Serializer):
    id = serializers.UUIDField()
    title = serializers.CharField()
    icon = serializers.ChoiceField(choices=ICONS)
    measure = serializers.ChoiceField(choices=Challenge.Measure.choices)
    unit = serializers.CharField()


class TodayChallengeOut(ChallengeBriefOut):
    """One of my challenges today: what to show on its card and in the ring."""

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
    proofs = ProofOut(many=True, help_text="Today's proofs, uploads in flight too.")
    proof_days = serializers.ListField(
        child=serializers.DateField(), help_text="Days of this week with proof."
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
    proof_days = serializers.ListField(
        child=serializers.DateField(), help_text="Days of the month with proof."
    )


class BoardOut(serializers.Serializer):
    days = serializers.ListField(child=serializers.DateField())
    rows = BoardRowOut(many=True)


class ProofStartIn(serializers.Serializer):
    kind = serializers.ChoiceField(choices=Proof.Kind.choices)
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
