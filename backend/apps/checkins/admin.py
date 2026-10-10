from django.contrib import admin

from .models import CheckIn, CheckInEntry


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


@admin.register(CheckInEntry)
class CheckInEntryAdmin(admin.ModelAdmin):
    list_display = ("check_in", "number", "amount", "created_at")
    list_filter = ("crew",)
    raw_id_fields = ("check_in",)
