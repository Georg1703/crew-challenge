# Recipe: a soft-deleted model

Use it for anything people create and later delete but we must keep: challenges, proofs,
comments. Deleting sets `deleted_at`; the row stays for history, audit and restore.

1. Inherit the base:
   - crew-owned rows: `apps.crews.models.CrewScopedSoftDeleteModel`
   - anything else: `apps.core.models.SoftDeleteModel`
   ```python
   class Challenge(CrewScopedSoftDeleteModel):
       title = models.CharField(max_length=60)

       class Meta(CrewScopedSoftDeleteModel.Meta):
           constraints = [
               # Unique rules apply only to rows that are not deleted.
               models.UniqueConstraint(
                   fields=["crew", "title"],
                   condition=models.Q(deleted_at__isnull=True),
                   name="challenge_unique_title_per_crew",
               ),
           ]
   ```
   If the model sets its own `Meta`, inherit the base `Meta` so `base_manager_name` is kept.
2. Read through `Model.objects` (only rows that are not deleted). Use `Model.all_objects` only
   for history screens, the Django admin and restore.
3. Delete in a service with `instance.delete()` or `queryset.delete()`. Both are soft and use
   `apps.core.clock`. `hard_delete()` exists for admin clean-ups and tests only.
4. Foreign keys to a deleted row still resolve (the base manager is `all_objects`), so old votes
   or check-ins keep showing what they pointed at. Filter deleted rows out in selectors where
   the screen should not show them.
5. In `admin.py`, list `all_objects` and add `deleted_at` to `list_filter`:
   ```python
   def get_queryset(self, request):
       return Challenge.all_objects.all()
   ```
6. Tests: the default manager hides the deleted row, `all_objects` sees it, a queryset delete is
   soft. See `apps/core/tests/test_soft_delete.py`.
