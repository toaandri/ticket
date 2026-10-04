"""PostgreSQL integration fixtures; pytest-django manages database creation."""

import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def auth_client(db):
    def authenticate(user):
        client = APIClient()
        refresh = RefreshToken.for_user(user)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
        return client

    return authenticate


@pytest.fixture(autouse=True)
def clear_throttle_cache():
    from django.core.cache import cache

    cache.clear()
    yield
    cache.clear()
