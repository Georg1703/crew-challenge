from typing import Any

from django.contrib import admin
from django.db.models import QuerySet
from django.http import HttpRequest

from .models import Challenge, Participant, Vote


class ParticipantInline(admin.TabularInline):
    """Who takes part, on the challenge's own page (one row per member: no half-made rows)."""

    model = Participant
    fields = ("member", "left_on")
    extra = 0


@admin.register(Challenge)
class ChallengeAdmin(admin.ModelAdmin):
    inlines = (ParticipantInline,)
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
        """New participant rows belong to the challenge's crew."""
        rows = formset.save(commit=False)
        for row in rows:
            row.crew_id = form.instance.crew_id
            row.save()
        for row in formset.deleted_objects:
            row.delete()
        formset.save_m2m()


@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    list_display = ("challenge", "member", "left_on", "created_at")
    list_filter = ("crew",)


@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display = ("challenge", "member", "created_at")
    list_filter = ("crew",)
