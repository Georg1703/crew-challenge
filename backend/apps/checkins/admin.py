from typing import Any

from django.contrib import admin
from django.db.models import QuerySet
from django.http import HttpRequest

from .models import CheckIn, CheckInEntry, Proof


class EntryInline(admin.TabularInline):
    model = CheckInEntry
    extra = 0
    fields = ("number", "amount", "created_at")
    readonly_fields = ("created_at",)


@admin.register(CheckIn)
class CheckInAdmin(admin.ModelAdmin):
    list_display = ("challenge", "member", "day", "status", "amount")
    list_filter = ("crew", "status")
    date_hierarchy = "day"
    inlines = [EntryInline]


@admin.register(Proof)
class ProofAdmin(admin.ModelAdmin):
    list_display = ("check_in", "kind", "status", "created_at", "deleted_at")
    list_filter = ("crew", "kind", "status", "deleted_at")
    raw_id_fields = ("check_in", "original", "thumb")

    def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
        return Proof.all_objects.all()  # removed proofs too
