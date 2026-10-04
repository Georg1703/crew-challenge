from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.authentication import BaseAuthentication
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core import health


class HealthView(APIView):
    """GET /api/health -> 200 when the database and Redis respond, 503 otherwise."""

    authentication_classes: list[type[BaseAuthentication]] = []  # no session, no CSRF
    permission_classes = [AllowAny]

    @extend_schema(exclude=True)
    def get(self, request: Request) -> Response:
        ok, checks = health.run_checks()
        return Response(
            {"status": "ok" if ok else "error", "checks": checks},
            status=status.HTTP_200_OK if ok else status.HTTP_503_SERVICE_UNAVAILABLE,
        )
