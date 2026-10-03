from django.contrib.auth import login, logout
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.authentication import BaseAuthentication
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts import services
from apps.core.throttling import LoginRateThrottle

from .serializers import CsrfOut, LoginIn


class CsrfView(APIView):
    """GET /api/v1/auth/csrf - sets the csrftoken cookie; call it before the first POST."""

    authentication_classes: list[type[BaseAuthentication]] = []
    permission_classes = [AllowAny]

    @extend_schema(responses=CsrfOut, operation_id="auth_csrf")
    @method_decorator(ensure_csrf_cookie)
    def get(self, request: Request) -> Response:
        return Response({"csrf_token": get_token(request)})


class LoginView(APIView):
    """POST /api/v1/auth/login - starts a session. Then call GET /api/v1/me."""

    permission_classes = [AllowAny]
    throttle_classes = [LoginRateThrottle]

    @extend_schema(request=LoginIn, responses={204: None}, operation_id="auth_login")
    def post(self, request: Request) -> Response:
        data = LoginIn(data=request.data)
        data.is_valid(raise_exception=True)
        user = services.verify_credentials(**data.validated_data)
        login(request, user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class LogoutView(APIView):
    """POST /api/v1/auth/logout - ends the session."""

    permission_classes = [IsAuthenticated]

    @extend_schema(request=None, responses={204: None}, operation_id="auth_logout")
    def post(self, request: Request) -> Response:
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)
