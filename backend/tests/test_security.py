import pytest
from django.core.cache import cache
from django.test import override_settings
from rest_framework.test import APIClient
from rest_framework.throttling import ScopedRateThrottle

pytestmark = pytest.mark.django_db


def test_cors_and_session_csrf_policy(inventory_demo):
    owner, *_ = inventory_demo
    client = APIClient(enforce_csrf_checks=True)
    good = client.options(
        "/api/v1/events/", HTTP_ORIGIN="http://localhost:5173", HTTP_ACCESS_CONTROL_REQUEST_METHOD="GET"
    )
    assert good["Access-Control-Allow-Origin"] == "http://localhost:5173"
    foreign = client.options(
        "/api/v1/events/", HTTP_ORIGIN="https://untrusted.example", HTTP_ACCESS_CONTROL_REQUEST_METHOD="GET"
    )
    assert "Access-Control-Allow-Origin" not in foreign
    client.force_login(owner)
    denied = client.post("/api/v1/organizations/", {"name": "CSRF attempt", "slug": "csrf-attempt"}, format="json")
    assert denied.status_code == 403
    assert "CSRF" in str(denied.data)


def test_login_throttle_limits_invalid_attempts(monkeypatch):
    with override_settings(
        CACHES={
            "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "LOCATION": "security-throttle"}
        }
    ):
        cache.clear()
        monkeypatch.setattr(ScopedRateThrottle, "THROTTLE_RATES", {"login": "2/min"})
        client = APIClient()
        for _ in range(2):
            assert (
                client.post(
                    "/api/v1/auth/login/", {"email": "missing@example.com", "password": "invalid"}, format="json"
                ).status_code
                == 401
            )
        response = client.post(
            "/api/v1/auth/login/", {"email": "missing@example.com", "password": "invalid"}, format="json"
        )
        assert response.status_code == 429 and response["Retry-After"]
