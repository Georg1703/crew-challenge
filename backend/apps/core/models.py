"""Abstract base models shared by every app.

- `TimeStampedModel`: UUID primary key, `created_at`, `updated_at`.
- `SoftDeleteModel`: adds `deleted_at`; deleting keeps the row (see the class docstring).

`CrewScopedModel` and `CrewScopedSoftDeleteModel` (a crew foreign key plus `.for_crew(crew)`)
live in the `crews` app, because core must not depend on domain apps.
"""

from __future__ import annotations

import uuid
from typing import Any

from django.db import models

from apps.core import clock


class TimeStampedModel(models.Model):
    """UUID primary key plus UTC creation and update timestamps."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ("-created_at",)


class SoftDeleteQuerySet[M: models.Model](models.QuerySet[M]):
    """Rows are never removed by `.delete()`; they get a `deleted_at` time instead."""

    def alive(self) -> SoftDeleteQuerySet[M]:
        return self.filter(deleted_at__isnull=True)

    def dead(self) -> SoftDeleteQuerySet[M]:
        return self.filter(deleted_at__isnull=False)

    def delete(self) -> tuple[int, dict[str, int]]:
        now = clock.now()
        count = self.filter(deleted_at__isnull=True).update(deleted_at=now, updated_at=now)
        return count, {self.model._meta.label: count}

    def hard_delete(self) -> tuple[int, dict[str, int]]:
        """Really remove the rows. Only for admin clean-ups and tests."""
        return super().delete()


class SoftDeleteManager[M: models.Model](models.Manager[M]):
    """The default manager of a soft-deletable model: only rows that are not deleted."""

    def get_queryset(self) -> SoftDeleteQuerySet[M]:
        return SoftDeleteQuerySet(self.model, using=self._db).alive()


class SoftDeleteModel(TimeStampedModel):
    """Abstract base for rows people can delete but we keep (history, audit, restore).

    - `Model.objects` returns only rows that are not deleted. Use it everywhere.
    - `Model.all_objects` returns every row (admin, history, restore).
    - `instance.delete()` and `queryset.delete()` set `deleted_at`; nothing is removed.
    - Foreign keys still reach a deleted row (`base_manager_name = "all_objects"`).
    - Unique constraints should add `condition=Q(deleted_at__isnull=True)`.
    """

    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)

    objects = SoftDeleteManager()
    all_objects = SoftDeleteQuerySet.as_manager()

    class Meta(TimeStampedModel.Meta):
        abstract = True
        base_manager_name = "all_objects"

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    def delete(self, using: Any = None, keep_parents: bool = False) -> tuple[int, dict[str, int]]:
        if self.deleted_at is None:
            self.deleted_at = clock.now()
            self.save(update_fields=["deleted_at", "updated_at"])
        return 1, {self._meta.label: 1}

    def hard_delete(self) -> tuple[int, dict[str, int]]:
        """Really remove the row. Only for admin clean-ups and tests."""
        return super().delete()

    def restore(self) -> None:
        self.deleted_at = None
        self.save(update_fields=["deleted_at", "updated_at"])
