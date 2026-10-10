from typing import Any

from django.contrib import admin
from django.db.models import QuerySet
from django.http import HttpRequest

from .models import Comment


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    """Every comment, deleted ones too (restore one by clearing `deleted_at`)."""

    list_display = ("created_at", "member", "level", "text", "target_type", "deleted_at")
    list_filter = ("crew", "deleted_at")
    search_fields = ("text",)
    raw_id_fields = ("member", "parent")

    def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
        return Comment.all_objects.all()
