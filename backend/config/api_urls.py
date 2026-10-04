"""API v1 URL routing."""

from django.urls import include, path

urlpatterns = [
    path("", include("apps.events.urls")),
    path("", include("apps.accounts.urls")),
    path("", include("apps.organizations.urls")),
]
