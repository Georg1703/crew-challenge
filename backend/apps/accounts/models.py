import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """A person who can log in. Crew membership lives in crews.Member (one user, many crews)."""

    class Language(models.TextChoices):
        ROMANIAN = "ro", "Romana"
        ENGLISH = "en", "English"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    preferred_language = models.CharField(
        max_length=2, choices=Language.choices, default=Language.ROMANIAN
    )

    def __str__(self) -> str:
        return self.username
