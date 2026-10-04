"""JSON error pages for the API.

DRF formats errors raised inside its views. Two cases never reach DRF and would otherwise return
Django's HTML pages: a URL that matches no route (404) and an unhandled exception (500). For paths
under /api/ these handlers return the standard error shape; other paths (admin) keep Django's pages.

Django uses them only when DEBUG is False (locally you see the debug page instead).
"""

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views import defaults

API_PREFIX = "/api/"


def _is_api(request: HttpRequest) -> bool:
    return request.path.startswith(API_PREFIX)


def _error(code: str, message: str, status: int) -> JsonResponse:
    return JsonResponse({"error": {"code": code, "message": message}}, status=status)


def not_found(request: HttpRequest, exception: Exception | None = None) -> HttpResponse:
    if _is_api(request):
        return _error("not_found", "Not found.", 404)
    return defaults.page_not_found(request, exception or Exception("Not found"))


def server_error(request: HttpRequest) -> HttpResponse:
    # Django has already logged the exception (logger "django.request") before calling this.
    if _is_api(request):
        return _error("server_error", "Something went wrong on our side. Please try again.", 500)
    return defaults.server_error(request)
