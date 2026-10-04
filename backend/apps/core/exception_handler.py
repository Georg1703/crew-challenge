"""DRF exception handler: every API error gets the same shape.

    {"error": {"code": "...", "message": "...", "fields": {...}}}

`fields` is present only for validation errors. Unhandled exceptions are left to Django (500).
"""

from __future__ import annotations

from typing import Any

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.http import Http404
from rest_framework import exceptions as drf
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

from .errors import DomainError

# DRF's default codes, renamed where ours are clearer for the frontend.
_CODE_ALIASES = {
    "invalid": "validation_failed",
    "authentication_failed": "not_authenticated",
}


def exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    if isinstance(exc, DomainError):
        return Response({"error": exc.as_dict()}, status=exc.status_code)

    if isinstance(exc, Http404):
        exc = drf.NotFound()
    elif isinstance(exc, DjangoPermissionDenied):
        exc = drf.PermissionDenied()

    response = drf_exception_handler(exc, context)
    if response is None or not isinstance(exc, drf.APIException):
        return response

    if isinstance(exc, drf.ValidationError):
        body = {
            "code": "validation_failed",
            "message": "Some fields are not valid.",
            "fields": _field_errors(exc.detail),
        }
    else:
        code = _first_code(exc)
        body = {"code": _CODE_ALIASES.get(code, code), "message": _first_message(exc.detail)}

    response.data = {"error": body}
    return response


def _field_errors(detail: Any) -> dict[str, list[str]]:
    if isinstance(detail, dict):
        return {str(key): _messages(value) for key, value in detail.items()}
    return {"non_field_errors": _messages(detail)}


def _messages(value: Any) -> list[str]:
    if isinstance(value, list):
        out: list[str] = []
        for item in value:
            out.extend(_messages(item))
        return out
    if isinstance(value, dict):
        return [f"{k}: {m}" for k, v in value.items() for m in _messages(v)]
    return [str(value)]


def _first_code(exc: drf.APIException) -> str:
    codes = exc.get_codes()
    while isinstance(codes, list | dict):
        codes = next(iter(codes.values()), "error") if isinstance(codes, dict) else codes[0]
    return str(codes)


def _first_message(detail: Any) -> str:
    messages = _messages(detail) if not isinstance(detail, str) else [detail]
    return messages[0] if messages else "Something went wrong."
