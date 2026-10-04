"""Abstract base models shared by every app.

`CrewScopedModel` (a crew foreign key plus `.for_crew(crew)`) is added together with the
`crews` app, because core must not depend on domain apps.
"""

import uuid

from django.db import models


class TimeStampedModel(models.Model):
    """UUID primary key plus UTC creation and update timestamps."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ("-created_at",)
