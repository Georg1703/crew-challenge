from typing import Any

from django.contrib import admin
from django.db.models import QuerySet
from django.http import HttpRequest

from .models import Comment, CommentRead


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    """Every comment, deleted ones too (restore one by clearing `deleted_at`)."""

    list_display = ("created_at", "member", "level", "text", "target_type", "deleted_at")
    list_filter = ("crew", "deleted_at")
    search_fields = ("text",)
    raw_id_fields = ("member", "parent")

    def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
        return Comment.all_objects.all()


@admin.register(CommentRead)
class CommentReadAdmin(admin.ModelAdmin):
    """When each member last saw each card's comments (what makes the others' unread)."""

    list_display = ("member", "target_type", "target_id", "read_at")
    list_filter = ("crew",)
    raw_id_fields = ("member",)
