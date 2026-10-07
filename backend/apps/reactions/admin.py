from django.contrib import admin

from .models import Reaction


@admin.register(Reaction)
class ReactionAdmin(admin.ModelAdmin):
    list_display = ("emoji", "member", "target_type", "target_id", "crew", "created_at")
    list_filter = ("crew", "target_type")
    raw_id_fields = ("member",)
