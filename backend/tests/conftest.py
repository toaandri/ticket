"""
pytest configuration for Ticket backend tests.

Uses real PostgreSQL (not SQLite) for all integration and concurrency tests.
"""

import django
import pytest
from django.conf import settings


@pytest.fixture(scope="session")
def django_db_setup():
    """Use the DATABASE_URL from env — real PostgreSQL required."""
    pass


@pytest.fixture
def api_client():
    """DRF API test client."""
    from rest_framework.test import APIClient

    return APIClient()


@pytest.fixture
def auth_client(api_client, db):
    """Return a helper that returns an authenticated APIClient for a given user."""

    def _auth(user):
        from rest_framework_simplejwt.tokens import RefreshToken

        refresh = RefreshToken.for_user(user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
        return api_client

    return _auth
