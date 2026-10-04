from typing import Any

from django.contrib import admin
from django.db.models import QuerySet
from django.http import HttpRequest

from .models import Challenge, Participation, Round, Vote


@admin.register(Round)
class RoundAdmin(admin.ModelAdmin):
    list_display = ("crew", "period_kind", "period_start", "state", "chosen", "chosen_by")
    list_filter = ("crew", "state", "period_kind")


@admin.register(Challenge)
class ChallengeAdmin(admin.ModelAdmin):
    list_display = ("title", "crew", "round", "state", "created_by", "created_at", "deleted_at")
    list_filter = ("crew", "state", "deleted_at")
    search_fields = ("title",)

    def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
        return Challenge.all_objects.all()  # deleted proposals too


@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display = ("round", "member", "challenge", "created_at")
    list_filter = ("crew",)


@admin.register(Participation)
class ParticipationAdmin(admin.ModelAdmin):
    list_display = ("challenge", "member", "joined_on", "ended_on")
    list_filter = ("crew",)
