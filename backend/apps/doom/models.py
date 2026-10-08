"""The Wheel of Doom: spins owed for failed windows, drawn on the server, served with proof.

A spin is opened for every missing check-in (or one missed total) in a window that ended below its
need (`checkins.days.judge`), on a challenge with punishments. Drawing picks one of the
challenge's punishments before the dial turns; it is served by a shown proof, or "Done" when the
punishment needs none. Whether it is served is derived, like verdicts. Rules live in services.py.
"""

from __future__ import annotations

from django.contrib.contenttypes.fields import GenericRelation
from django.db import models

from apps.challenges.models import Challenge, Punishment
from apps.crews.models import CrewScopedModel, Member


class Spin(CrewScopedModel):
    """One turn of the wheel owed by one participant for one failed window."""

    challenge = models.ForeignKey(Challenge, on_delete=models.CASCADE, related_name="spins")
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name="spins")
    window_first = models.DateField(help_text="The failed window it came from.")
    window_last = models.DateField()
    number = models.PositiveSmallIntegerField(help_text="1, 2... within its window.")
    need = models.DecimalField(max_digits=10, decimal_places=2, help_text="What the window asked.")
    done = models.DecimalField(max_digits=12, decimal_places=2, help_text="What was done in it.")
    punishment = models.ForeignKey(
        Punishment,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
        help_text="Drawn on the server; empty until then.",
    )
    drawn_at = models.DateTimeField(null=True, blank=True)
    serve_by = models.DateField(null=True, blank=True, help_text="The draw's crew-local day + 7.")
    done_at = models.DateTimeField(
        null=True, blank=True, help_text='"Done", for a punishment that needs no proof.'
    )
    # Proofs and reactions point here by a generic key; these delete them with the spin.
    proofs = GenericRelation(
        "proofs.Proof",
        content_type_field="subject_type",
        object_id_field="subject_id",
        related_query_name="spin",
    )
    reactions = GenericRelation(
        "reactions.Reaction", content_type_field="target_type", object_id_field="target_id"
    )

    class Meta:
        ordering = ("window_first", "number")
        constraints = [
            models.UniqueConstraint(
                fields=["challenge", "member", "window_first", "number"], name="spin_once"
            )
        ]

    def __str__(self) -> str:
        return f"{self.member} {self.challenge} {self.window_first} #{self.number}"
