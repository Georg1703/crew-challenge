from rest_framework import serializers

from apps.challenges.api.serializers import PersonOut, PunishmentOut
from apps.challenges.models import Challenge
from apps.checkins.api.serializers import ChallengeBriefOut
from apps.comments.api.serializers import CommentSummaryOut
from apps.journal.models import JournalEntry
from apps.proofs.api.serializers import ProofOut
from apps.reactions.api.serializers import ReactionSummaryOut


class CheckInFactsOut(serializers.Serializer):
    """A check-in post's card, as it was when posted."""

    action = serializers.ChoiceField(
        choices=["check", "amount", "files"],
        help_text="The day's check-in, a number added, or photos and videos added later.",
    )
    amount = serializers.FloatField(allow_null=True, help_text="The number added.")
    total = serializers.FloatField(allow_null=True, help_text="The day's total after this post.")
    target = serializers.FloatField(allow_null=True, help_text="The least amount a day needs.")
    streak = serializers.IntegerField(allow_null=True, help_text="Days or weeks in a row then.")
    milestone = serializers.IntegerField(
        allow_null=True, help_text="3, 7, 14 or 30: the streak this post reached."
    )
    proofs = serializers.IntegerField(help_text="Photos and videos posted with it.")


class FailedFactsOut(serializers.Serializer):
    """A failed window's card, as its spins opened: what failed and how many spins it owes."""

    window_first = serializers.DateField()
    window_last = serializers.DateField()
    need_kind = serializers.ChoiceField(choices=Challenge.NeedKind.choices)
    need = serializers.FloatField()
    done = serializers.FloatField()
    spins = serializers.IntegerField(help_text="Spins the window owes.")


class SpinFactsOut(serializers.Serializer):
    """A spin's card when drawn: what failed and what was drawn."""

    window_first = serializers.DateField()
    window_last = serializers.DateField()
    need_kind = serializers.ChoiceField(choices=Challenge.NeedKind.choices)
    need = serializers.FloatField()
    done = serializers.FloatField()
    punishment = PunishmentOut()
    serve_by = serializers.DateField(allow_null=True)


class ServedFactsOut(serializers.Serializer):
    punishment = PunishmentOut()
    proofs = serializers.IntegerField(help_text="Photos and videos it was served with.")


class CrewDayFactsOut(serializers.Serializer):
    members = serializers.ListField(
        child=serializers.UUIDField(), help_text="Everyone who was due that day."
    )


class JournalEntryOut(serializers.Serializer):
    """One card: written once when its post was made, never changed. Its kind's facts are set,
    the others null."""

    id = serializers.UUIDField()
    kind = serializers.ChoiceField(choices=JournalEntry.Kind.choices)
    at = serializers.DateTimeField(help_text="When it was posted: the journal's order.")
    day = serializers.DateField(help_text="The crew-local day it sits under.")
    member = PersonOut(allow_null=True, help_text="Who did it; null for the crew's day.")
    challenge = ChallengeBriefOut(allow_null=True, help_text="On what; null for the crew's day.")
    proofs = ProofOut(many=True, help_text="The photos and videos posted with it.")
    reactions = ReactionSummaryOut(help_text="Target `entry`, this card's id.")
    comments = CommentSummaryOut(help_text="Target `entry`, this card's id.")
    check_in = CheckInFactsOut(allow_null=True)
    failed = FailedFactsOut(allow_null=True)
    spin = SpinFactsOut(allow_null=True)
    served = ServedFactsOut(allow_null=True)
    crew_day = CrewDayFactsOut(allow_null=True)


class JournalDayOut(serializers.Serializer):
    day = serializers.DateField()
    check_ins = serializers.IntegerField(help_text="One per person and challenge.")
    proofs = serializers.IntegerField(help_text="Photos and videos posted that day.")


class JournalPageOut(serializers.Serializer):
    results = JournalEntryOut(many=True)
    days = JournalDayOut(many=True, help_text="The counts of each day on this page, for dividers.")
    next = serializers.CharField(allow_null=True, help_text="Send as `cursor` for the next page.")
