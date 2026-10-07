from types import SimpleNamespace

import pytest
from django.db import transaction

from apps.accounts.models import User
from config.exceptions import custom_exception_handler

pytestmark = pytest.mark.django_db


def test_unexpected_api_error_rolls_back_request_writes(settings):
    settings.DATABASES["default"]["ATOMIC_REQUESTS"] = True
    with transaction.atomic():
        User.objects.create_user("failed-request@example.com", "example-password-93!")
        response = custom_exception_handler(
            RuntimeError("Synthetic failure"), {"request": SimpleNamespace(id="request-1")}
        )
        assert response.status_code == 500
        assert response.data["request_id"] == "request-1"
        assert response.data["details"] is None
        assert transaction.get_rollback()
    assert not User.objects.filter(email="failed-request@example.com").exists()
