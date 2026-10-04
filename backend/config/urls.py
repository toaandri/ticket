"""URL configuration for Ticket platform."""

from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

from config.health import HealthCheckView

urlpatterns = [
    # Health check (used by Docker Compose healthcheck)
    path("api/health/", HealthCheckView.as_view(), name="health"),
    # Django admin
    path("admin/", admin.site.urls),
    # OpenAPI schema
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/schema/swagger-ui/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/schema/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    # API v1
    path("api/v1/", include("config.api_urls")),
]
