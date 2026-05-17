"""Root URL configuration.

API endpoints are versioned (/api/v1/...). Schema and docs are exposed at
/api/schema/, /api/docs/ (Swagger UI), /api/redoc/.
"""
from __future__ import annotations

from django.conf import settings
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)


def health(_request) -> JsonResponse:
    """Liveness probe. Used by load balancers and orchestrators."""
    return JsonResponse({"status": "ok"})


api_v1_patterns = [
    path("auth/", include("apps.authentication.urls")),
    path("users/", include("apps.users.urls")),
    path("subscriptions/", include("apps.subscriptions.urls")),
    path("api-keys/", include("apps.api_keys.urls")),
    path("dashboard/", include("apps.dashboard.urls")),
]

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", health, name="health"),
    # API v1
    path("api/v1/", include((api_v1_patterns, "v1"), namespace="v1")),
    # OpenAPI
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]

if settings.DEBUG:
    try:
        import debug_toolbar  # noqa: F401

        urlpatterns += [path("__debug__/", include("debug_toolbar.urls"))]
    except ImportError:
        pass
