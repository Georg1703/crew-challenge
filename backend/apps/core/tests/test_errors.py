from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.http import Http404
from rest_framework import exceptions as drf
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory
from rest_framework.views import APIView

from apps.core import errors
from apps.core.exception_handler import exception_handler


class InviteExpired(errors.Conflict):
    code = "invite_expired"
    message = "This invite link has expired. Ask for a new one."


def handle(exc):
    return exception_handler(exc, {})


def test_domain_error_uses_class_defaults():
    err = InviteExpired()
    assert err.as_dict() == {"code": "invite_expired", "message": InviteExpired.message}
    assert str(err) == InviteExpired.message


def test_domain_error_overrides_and_fields():
    err = errors.ValidationFailed("Bad input", code="bad_input", fields={"name": ("Too short.",)})
    assert err.as_dict() == {
        "code": "bad_input",
        "message": "Bad input",
        "fields": {"name": ["Too short."]},
    }


def test_domain_error_response():
    response = handle(InviteExpired())
    assert response.status_code == 409
    assert response.data == {"error": {"code": "invite_expired", "message": InviteExpired.message}}


def test_validation_error_with_field_messages():
    exc = drf.ValidationError({"password": ["Too short."], "profile": {"age": ["Required."]}})
    response = handle(exc)
    assert response.status_code == 400
    assert response.data == {
        "error": {
            "code": "validation_failed",
            "message": "Some fields are not valid.",
            "fields": {"password": ["Too short."], "profile": ["age: Required."]},
        }
    }


def test_validation_error_without_fields():
    response = handle(drf.ValidationError(["Pick at least one proof type."]))
    assert response.data["error"]["fields"] == {
        "non_field_errors": ["Pick at least one proof type."]
    }


def test_django_404_and_permission_denied_are_mapped():
    not_found = handle(Http404())
    assert not_found.status_code == 404
    assert not_found.data["error"]["code"] == "not_found"

    denied = handle(DjangoPermissionDenied())
    assert denied.status_code == 403
    assert denied.data["error"]["code"] == "permission_denied"


def test_drf_errors_keep_their_codes():
    throttled = handle(drf.Throttled(wait=10))
    assert throttled.status_code == 429
    assert throttled.data["error"]["code"] == "throttled"

    failed = handle(drf.AuthenticationFailed())
    assert failed.data["error"]["code"] == "not_authenticated"


def test_unknown_exceptions_are_left_to_django():
    assert handle(RuntimeError("boom")) is None


class _PrivateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"ok": True})


def test_anonymous_request_gets_401_not_403():
    request = APIRequestFactory().get("/private")
    response = _PrivateView.as_view()(request)
    assert response.status_code == 401
    assert response.data == {
        "error": {
            "code": "not_authenticated",
            "message": "Authentication credentials were not provided.",
        }
    }
