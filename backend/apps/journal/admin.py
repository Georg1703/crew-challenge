from django.contrib import admin

from .models import JournalEntry


@admin.register(JournalEntry)
class JournalEntryAdmin(admin.ModelAdmin):
    """The stored cards, written by the apps that post; `journal_backfill` rebuilds missing ones."""

    list_display = ("created_at", "day", "kind", "member", "challenge", "crew")
    list_filter = ("crew", "kind", "day")
    date_hierarchy = "day"
