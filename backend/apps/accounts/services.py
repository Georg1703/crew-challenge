"""Account rules: usernames, passwords, credentials, preferences.

Usernames are stored in lowercase so "Ana" and "ana" are the same person on a phone keyboard.
"""

from __future__ import annotations

import string
import unicodedata

from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction

from apps.core.errors import DomainError, ValidationFailed

from .models import User

USERNAME_MIN, USERNAME_MAX = 3, 30
USERNAME_CHARACTERS = set(string.ascii_lowercase + string.digits + "._-")


class InvalidCredentials(DomainError):
    code = "invalid_credentials"
    message = "Wrong username or password."
    status_code = 400


class UsernameTaken(ValidationFailed):
    code = "username_taken"
    message = "This username is already taken."


def normalize_username(username: str) -> str:
    return unicodedata.normalize("NFKC", username).strip().lower()


def validate_new_username(username: str) -> str:
    """Return the normalized username or raise ValidationFailed / UsernameTaken."""
    normalized = normalize_username(username)
    if not USERNAME_MIN <= len(normalized) <= USERNAME_MAX or not set(normalized) <= (
        USERNAME_CHARACTERS
    ):
        raise ValidationFailed(
            fields={
                "username": [
                    f"Use {USERNAME_MIN}-{USERNAME_MAX} letters, digits, dots, dashes "
                    "or underscores."
                ]
            }
        )
    if User.objects.filter(username=normalized).exists():
        raise UsernameTaken(fields={"username": [UsernameTaken.message]})
    return normalized


def create_user(*, username: str, password: str, language: str | None = None) -> User:
    """Create a login. Validates the username and the password strength."""
    normalized = validate_new_username(username)
    candidate = User(username=normalized)
    if language is not None:
        if language not in User.Language.values:
            raise ValidationFailed(fields={"preferred_language": ["Unknown language."]})
        candidate.preferred_language = language
    try:
        validate_password(password, user=candidate)
    except DjangoValidationError as exc:
        raise ValidationFailed(fields={"password": list(exc.messages)}) from exc
    candidate.set_password(password)
    try:
        with transaction.atomic():
            candidate.save()
    except IntegrityError as exc:  # someone took the name in the same moment
        raise UsernameTaken(fields={"username": [UsernameTaken.message]}) from exc
    return candidate


def verify_credentials(*, username: str, password: str) -> User:
    """Return the active user for these credentials or raise InvalidCredentials."""
    user = authenticate(username=normalize_username(username), password=password)
    if not isinstance(user, User):
        raise InvalidCredentials()
    return user


def set_preferred_language(*, user: User, language: str) -> User:
    if language not in User.Language.values:
        raise ValidationFailed(
            fields={"preferred_language": [f"Choose one of: {', '.join(User.Language.values)}."]}
        )
    user.preferred_language = language
    user.save(update_fields=["preferred_language"])
    return user
