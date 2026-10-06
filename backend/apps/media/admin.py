from typing import Any

from django.contrib import admin
from django.db.models import QuerySet
from django.http import HttpRequest

from .models import Transcode, Upload


@admin.register(Upload)
class UploadAdmin(admin.ModelAdmin):
    list_display = ("key", "crew", "mode", "status", "size", "created_at", "deleted_at")
    list_filter = ("crew", "mode", "status", "deleted_at")
    search_fields = ("key",)

    def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
        return Upload.all_objects.all()  # deleted files too


@admin.register(Transcode)
class TranscodeAdmin(admin.ModelAdmin):
    list_display = ("upload", "status", "job_id", "created_at", "updated_at")
    list_filter = ("status",)
    raw_id_fields = ("upload",)
