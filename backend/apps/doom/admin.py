from django.contrib import admin

from .models import Spin


@admin.register(Spin)
class SpinAdmin(admin.ModelAdmin):
    list_display = ("member", "challenge", "window_first", "number", "punishment", "serve_by")
    list_filter = ("crew", "challenge")
    raw_id_fields = ("member", "challenge", "punishment")
    date_hierarchy = "window_first"
