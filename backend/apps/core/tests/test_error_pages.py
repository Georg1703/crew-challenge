"""Unknown /api/ URLs and crashes return the standard JSON error shape, not Django's HTML pages."""

import pytest
from django.urls import path
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

import config.urls


class _Crash(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        raise RuntimeError("boom")


urlpatterns = [*config.urls.urlpatterns, path("api/v1/crash", _Crash.as_view())]
handler404 = config.urls.handler404
handler500 = config.urls.handler500

pytestmark = pytest.mark.urls(__name__)


@pytest.fixture
def client(client):
    client.raise_request_exception = False  # behave like production: render the 500 handler
    return client


def test_unknown_api_url_returns_json_404(client):
    response = client.get("/api/v1/does-not-exist")
    assert response.status_code == 404
    assert response["Content-Type"] == "application/json"
    assert response.json() == {"error": {"code": "not_found", "message": "Not found."}}


@pytest.mark.django_db
def test_crash_in_api_returns_json_500(client):
    response = client.get("/api/v1/crash")
    assert response.status_code == 500
    assert response["Content-Type"] == "application/json"
    assert response.json()["error"]["code"] == "server_error"


def test_non_api_paths_keep_django_pages(client, rf):
    from apps.core.api import errors

    assert client.get("/not-api").status_code == 404
    assert client.get("/not-api")["Content-Type"].startswith("text/html")
    page = errors.server_error(rf.get("/admin/"))
    assert page.status_code == 500
    assert page["Content-Type"].startswith("text/html")
