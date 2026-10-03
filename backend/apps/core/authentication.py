from rest_framework import authentication, exceptions
from rest_framework.permissions import SAFE_METHODS
from rest_framework.request import Request


class SessionAuthentication(authentication.SessionAuthentication):
    """Session auth with two changes to DRF's default.

    1. Answers 401 (not 403) when nobody is logged in. DRF returns 403 unless the first
       authentication class provides a WWW-Authenticate header; the SPA relies on 401 to show login.
    2. Checks CSRF on every unsafe request, also for anonymous users. DRF only checks it for
       logged-in users, which would leave login and invite acceptance open to login CSRF.
       Views that opt out of authentication (authentication_classes = []) are not affected.
    """

    def authenticate(self, request: Request):  # type: ignore[no-untyped-def]
        result = super().authenticate(request)
        if result is None and request.method not in SAFE_METHODS:
            self.enforce_csrf(request)
        return result

    def authenticate_header(self, request: Request) -> str:
        return "Session"

    def enforce_csrf(self, request: Request) -> None:
        try:
            super().enforce_csrf(request)
        except exceptions.PermissionDenied as exc:
            raise exceptions.PermissionDenied(
                "CSRF check failed. Fetch /api/v1/auth/csrf and send the X-CSRFToken header.",
                code="csrf_failed",
            ) from exc
