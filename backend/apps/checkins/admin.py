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
