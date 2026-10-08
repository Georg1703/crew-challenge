from typing import Any

from django.contrib import admin
from django.core.exceptions import ValidationError
from django.db.models import QuerySet
from django.forms.models import BaseInlineFormSet
from django.http import HttpRequest

from . import services
from .models import Challenge, Participant, Punishment, Vote


class ParticipantInline(admin.TabularInline):
    """Who takes part, on the challenge's own page (one row per member: no half-made rows)."""

    model = Participant
    fields = ("member", "left_on")
    extra = 0


class PunishmentFormSet(BaseInlineFormSet):
    """The app's rules for punishments: none, or 2 to 8 different ones. (One a spin drew cannot be
    removed, only reworded: the admin refuses to delete what a spin protects.)"""

    def clean(self) -> None:
        super().clean()
        if any(self.errors):
            return
        kept = [
            services.PunishmentShape(f.cleaned_data["text"], f.cleaned_data["proof_required"])
            for f in self.forms
            if f.cleaned_data and not f.cleaned_data.get("DELETE")
        ]
        errors = services.punishment_errors(kept)
        if errors:
            raise ValidationError(errors)


class PunishmentInline(admin.TabularInline):
    """Editable here too, with the app's rules; numbered 1 to N in order (the dial's numbers),
    new ones at the end."""

    model = Punishment
    formset = PunishmentFormSet
    fields = ("position", "text", "proof_required")
    readonly_fields = ("position",)
    extra = 0
    max_num = services.PUNISHMENTS_MAX


@admin.register(Challenge)
class ChallengeAdmin(admin.ModelAdmin):
    inlines = (ParticipantInline, PunishmentInline)
    list_display = (
        "title",
        "crew",
        "state",
        "period_start",
        "start_date",
        "end_date",
        "created_by",
        "created_at",
        "deleted_at",
    )
    list_filter = ("crew", "state", "deleted_at")
    search_fields = ("title",)

    def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
        return Challenge.all_objects.all()  # deleted proposals too

    def save_formset(self, request: HttpRequest, form: Any, formset: Any, change: bool) -> None:
        """New rows belong to the challenge's crew. Punishments: the removed ones go first, the
        rest close up to 1..N, and new ones take the numbers after them."""
        rows = formset.save(commit=False)
        for row in formset.deleted_objects:
            row.delete()
        if formset.model is Punishment:
            services.number_punishments(challenge=form.instance)
            after = Punishment.objects.filter(challenge=form.instance).count()
            new = [row for row in rows if row._state.adding]
            for position, row in enumerate(new, start=after + 1):
                row.position = position
        for row in rows:
            row.crew_id = form.instance.crew_id
            if formset.model is Punishment and not row._state.adding:
                row.save(update_fields=["text", "proof_required", "updated_at"])  # keep its number
            else:
                row.save()
        formset.save_m2m()


@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    list_display = ("challenge", "member", "left_on", "created_at")
    list_filter = ("crew",)


@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display = ("challenge", "member", "created_at")
    list_filter = ("crew",)
