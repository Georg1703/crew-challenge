from typing import Any

from rest_framework import serializers

from apps.challenges.api.serializers import PersonOut, PunishmentOut
from apps.challenges.models import Challenge, Punishment
from apps.checkins.api.serializers import ChallengeBriefOut, DaySummaryOut
from apps.doom import selectors
from apps.doom.models import Spin
from apps.proofs.api.serializers import ProofOut, proof_data
from apps.reactions.api.serializers import ReactionSummaryOut

STATES = (selectors.PENDING, selectors.SPUN, selectors.SERVED)
DRAWN_STATES = (selectors.SPUN, selectors.SERVED)


class SpinOut(serializers.Serializer):
    """One of my spins: what it is for, the dial's punishments, and what was drawn."""

    id = serializers.UUIDField()
    challenge = ChallengeBriefOut()
    need_kind = serializers.ChoiceField(choices=Challenge.NeedKind.choices)
    window_first = serializers.DateField(help_text="The failed window it came from.")
    window_last = serializers.DateField()
    need = serializers.FloatField(help_text="What the window asked for.")
    done = serializers.FloatField(help_text="What was done in it.")
    punishments = PunishmentOut(many=True, help_text="The dial: every punishment, by position.")
    punishment = PunishmentOut(allow_null=True, help_text="The one drawn; null until the spin.")
    state = serializers.ChoiceField(choices=STATES)
    drawn_at = serializers.DateTimeField(allow_null=True)
    serve_by = serializers.DateField(allow_null=True, help_text="The draw's day + 7.")
    late = serializers.BooleanField(help_text="Spun, not served, and past `serve_by`.")
    proofs = ProofOut(many=True, help_text="My proofs on it, uploads in flight too.")


class OwedOut(serializers.Serializer):
    to_spin = serializers.IntegerField()
    to_serve = serializers.IntegerField(help_text="Drawn, not served yet.")
    spins = SpinOut(many=True, help_text="Not served yet, oldest window first.")


def punishment_data(punishment: Punishment | None) -> dict[str, Any] | None:
    if punishment is None:
        return None
    return {
        "position": punishment.position,
        "text": punishment.text,
        "proof_required": punishment.proof_required,
    }


def spin_data(spin: Spin, punishments: list[Punishment]) -> dict[str, Any]:
    return {
        "id": spin.pk,
        "challenge": spin.challenge,
        "need_kind": spin.challenge.need_kind,
        "window_first": spin.window_first,
        "window_last": spin.window_last,
        "need": spin.need,
        "done": spin.done,
        "punishments": [punishment_data(p) for p in punishments],
        "punishment": punishment_data(spin.punishment),
        "state": selectors.state(spin),
        "drawn_at": spin.drawn_at,
        "serve_by": spin.serve_by,
        "late": selectors.late(spin),
        "proofs": [proof_data(p) for p in spin.proofs.all()],
    }


class SpinItemOut(serializers.Serializer):
    """A spin in the crew's journal: who drew what (kind `spin`, as it was drawn, with the
    reactions), or who served it (kind `served`, with its proofs)."""

    id = serializers.UUIDField(help_text="The spin.")
    member = PersonOut()
    challenge = ChallengeBriefOut()
    day = serializers.DateField(help_text="The crew-local day it was drawn, or served.")
    window_first = serializers.DateField()
    window_last = serializers.DateField()
    need_kind = serializers.ChoiceField(choices=Challenge.NeedKind.choices)
    need = serializers.FloatField()
    done = serializers.FloatField()
    punishment = PunishmentOut()
    punishment_count = serializers.IntegerField(help_text="Arcs on the dial.")
    state = serializers.ChoiceField(choices=DRAWN_STATES)
    serve_by = serializers.DateField()
    late = serializers.BooleanField()
    proofs = ProofOut(many=True, help_text="Processing and ready proofs; empty on kind `spin`.")
    reactions = ReactionSummaryOut()
    day_summary = DaySummaryOut(help_text="The crew's whole day, for its divider.")
