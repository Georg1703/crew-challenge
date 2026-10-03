"""Root URL configuration.

- /api/health   liveness check (database + Redis), not versioned, not in the API contract
- /api/v1/...   the app's API; each app adds its own `api/urls.py` here
- /admin/       Django admin
"""

from django.conf import settings
from django.contrib import admin
from django.urls import URLPattern, URLResolver, include, path

from apps.core.api.views import HealthView

api_v1: list[URLPattern | URLResolver] = [
    # path("", include("apps.accounts.api.urls")),  # added with the accounts endpoints
]

urlpatterns = [
    path("api/health", HealthView.as_view(), name="health"),
    path("api/v1/", include(api_v1)),
    path("admin/", admin.site.urls),
]

if settings.DEBUG:  # pragma: no cover - local development only
    from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

    urlpatterns += [
        path("api/schema", SpectacularAPIView.as_view(), name="schema"),
        path("api/docs", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
    ]
