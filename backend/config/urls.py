"""Root URL configuration.

- /api/health   liveness check (database + Redis), not versioned, not in the API contract
- /api/v1/...   the app's API; each app adds its own `api/urls.py` here
- /admin/       Django admin

Unknown /api/ URLs and unhandled errors return the standard JSON error shape (handler404/500).
"""

from django.conf import settings
from django.contrib import admin
from django.urls import URLPattern, URLResolver, include, path

from apps.core.api.views import HealthView

api_v1: list[URLPattern | URLResolver] = [
    path("", include("apps.accounts.api.urls")),
    path("", include("apps.crews.api.urls")),
    path("", include("apps.challenges.api.urls")),
    path("", include("apps.checkins.api.urls")),
    path("", include("apps.media.api.urls")),
    path("", include("apps.reactions.api.urls")),
]

# JSON instead of HTML for unknown /api/ URLs and crashes (see apps/core/api/errors.py).
handler404 = "apps.core.api.errors.not_found"
handler500 = "apps.core.api.errors.server_error"

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

    if settings.OBJECT_STORAGE_BACKEND == "memory":  # make e2e: the browser uploads here, not S3
        from integrations.storage.memory import SERVED_AT
        from integrations.storage.memory_views import memory_bucket

        urlpatterns += [path(f"{SERVED_AT.lstrip('/')}<path:key>", memory_bucket)]
