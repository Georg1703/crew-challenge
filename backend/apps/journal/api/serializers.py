from rest_framework import serializers

from apps.checkins.api.serializers import FeedItemOut
from apps.doom.api.serializers import SpinItemOut
from apps.journal.selectors import CHECK_IN, SPIN

KINDS = (CHECK_IN, SPIN)


class JournalEntryOut(serializers.Serializer):
    kind = serializers.ChoiceField(choices=KINDS)
    activity_at = serializers.DateTimeField(help_text="The journal's order, latest first.")
    check_in = FeedItemOut(allow_null=True, help_text="Set when `kind` is check_in.")
    spin = SpinItemOut(allow_null=True, help_text="Set when `kind` is spin.")


class JournalPageOut(serializers.Serializer):
    results = JournalEntryOut(many=True)
    next = serializers.CharField(allow_null=True, help_text="Send as `cursor` for the next page.")
