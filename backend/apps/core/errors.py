"""Domain errors raised by services.

Services raise these (never DRF exceptions). The API exception handler turns every error into:

    {"error": {"code": "...", "message": "...", "fields": {...}}}

Define a subclass per business rule with a stable `code`, for example:

    class InviteExpired(Conflict):
        code = "invite_expired"
        message = "This invite link has expired. Ask for a new one."

The frontend translates `errors.<code>` and falls back to `message`.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

FieldErrors = Mapping[str, Sequence[str]]


class DomainError(Exception):
    code: str = "error"
    message: str = "Something went wrong."
    status_code: int = 400

    def __init__(
        self,
        message: str | None = None,
        *,
        code: str | None = None,
        fields: FieldErrors | None = None,
    ) -> None:
        self.message = message or type(self).message
        self.code = code or type(self).code
        self.fields: dict[str, list[str]] = {k: list(v) for k, v in (fields or {}).items()}
        super().__init__(self.message)

    def as_dict(self) -> dict[str, object]:
        body: dict[str, object] = {"code": self.code, "message": self.message}
        if self.fields:
            body["fields"] = self.fields
        return body


class ValidationFailed(DomainError):
    code = "validation_failed"
    message = "Some fields are not valid."
    status_code = 400


class PermissionDenied(DomainError):
    code = "permission_denied"
    message = "You are not allowed to do this."
    status_code = 403


class NotFound(DomainError):
    code = "not_found"
    message = "Not found."
    status_code = 404


class Conflict(DomainError):
    code = "conflict"
    message = "This conflicts with the current state."
    status_code = 409
