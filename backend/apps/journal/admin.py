from typing import Any

from django.contrib import admin
from django.http import HttpRequest

from .models import JournalEntry


@admin.register(JournalEntry)
class JournalEntryAdmin(admin.ModelAdmin):
    """The stored cards, read only: written by the apps that make posts (`journal_backfill` repairs
    them), compared here with the journal the app shows."""

    list_display = ("created_at", "day", "kind", "member", "challenge", "crew")
    list_filter = ("crew", "kind", "day")
    date_hierarchy = "day"
    readonly_fields = ("facts",)

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False
