from typing import Any

from django.contrib import admin
from django.db.models import QuerySet
from django.http import HttpRequest

from .models import Proof


@admin.register(Proof)
class ProofAdmin(admin.ModelAdmin):
    list_display = ("member", "subject_type", "kind", "status", "created_at", "deleted_at")
    list_filter = ("crew", "subject_type", "kind", "status", "deleted_at")
    raw_id_fields = ("member", "original", "thumb")

    def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
        return Proof.all_objects.all()  # removed proofs too
