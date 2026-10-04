import pytest
from django.db import IntegrityError, transaction

from apps.accounts.models import User

pytestmark = pytest.mark.django_db
PASSWORD = "correct-horse-ticket-93!"


def test_register_normalizes_email_hashes_password_and_returns_profile(api_client):
    response = api_client.post(
        "/api/v1/auth/register/",
        {
            "email": "Alice@Example.com",
            "password": PASSWORD,
            "display_name": "Alice",
        },
    )
    assert response.status_code == 201, response.data
    user = User.objects.get(email="alice@example.com")
    assert user.check_password(PASSWORD)
    assert user.password != PASSWORD
    assert "password" not in response.data["user"]
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
    profile = api_client.get("/api/v1/me/")
    assert profile.status_code == 200
    assert profile.data["email"] == "alice@example.com"


def test_registration_rejects_case_insensitive_duplicate(api_client):
    User.objects.create_user("alice@example.com", PASSWORD)
    response = api_client.post("/api/v1/auth/register/", {"email": "ALICE@example.com", "password": PASSWORD})
    assert response.status_code == 400
    assert User.objects.count() == 1


def test_database_rejects_case_variant_even_if_save_is_bypassed():
    User.objects.create_user("alice@example.com", PASSWORD)
    with pytest.raises(IntegrityError), transaction.atomic():
        User.objects.bulk_create([User(email="ALICE@example.com")])


def test_weak_password_is_rejected(api_client):
    response = api_client.post("/api/v1/auth/register/", {"email": "alice@example.com", "password": "123"})
    assert response.status_code == 400
    assert not User.objects.exists()


def test_login_refresh_rotation_logout(api_client):
    User.objects.create_user("alice@example.com", PASSWORD)
    login = api_client.post("/api/v1/auth/login/", {"email": "ALICE@example.com", "password": PASSWORD})
    assert login.status_code == 200, login.data
    old_refresh = login.data["refresh"]
    rotated = api_client.post("/api/v1/auth/refresh/", {"refresh": old_refresh})
    assert rotated.status_code == 200, rotated.data
    assert api_client.post("/api/v1/auth/refresh/", {"refresh": old_refresh}).status_code == 401
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {rotated.data['access']}")
    logout = api_client.post("/api/v1/auth/logout/", {"refresh": rotated.data["refresh"]})
    assert logout.status_code == 204, logout.data
    assert api_client.post("/api/v1/auth/refresh/", {"refresh": rotated.data["refresh"]}).status_code == 401


def test_foreign_refresh_cannot_be_revoked(auth_client):
    from rest_framework_simplejwt.tokens import RefreshToken

    alice = User.objects.create_user("alice@example.com", PASSWORD)
    bob = User.objects.create_user("bob@example.com", PASSWORD)
    refresh = RefreshToken.for_user(bob)
    client = auth_client(alice)
    assert client.post("/api/v1/auth/logout/", {"refresh": str(refresh)}).status_code == 400
    assert client.post("/api/v1/auth/refresh/", {"refresh": str(refresh)}).status_code == 200


def test_profile_update_does_not_allow_privilege_escalation(auth_client):
    user = User.objects.create_user("alice@example.com", PASSWORD)
    client = auth_client(user)
    response = client.patch(
        "/api/v1/me/", {"display_name": "New name", "is_staff": True, "is_superuser": True}, format="json"
    )
    assert response.status_code == 200
    user.refresh_from_db()
    assert user.display_name == "New name"
    assert not user.is_staff and not user.is_superuser


def test_anonymous_cannot_read_profile(api_client):
    assert api_client.get("/api/v1/me/").status_code == 401


def test_inactive_user_cannot_login(api_client):
    User.objects.create_user("alice@example.com", PASSWORD, is_active=False)
    assert (
        api_client.post("/api/v1/auth/login/", {"email": "alice@example.com", "password": PASSWORD}).status_code == 401
    )


def test_verification_token_sets_verified_timestamp_and_rejects_tampering(
    api_client, auth_client, mailoutbox, settings
):
    from apps.accounts.services import request_verification

    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    user = User.objects.create_user("alice@example.com", PASSWORD)
    request_verification(user)
    from apps.notifications.services import process_outbox

    process_outbox()
    token = mailoutbox[0].body.splitlines()[-1]
    assert api_client.post("/api/v1/auth/email-verify/", {"token": token + "x"}).status_code == 400
    assert api_client.post("/api/v1/auth/email-verify/", {"token": token}).status_code == 200
    user.refresh_from_db()
    assert user.email_verified_at is not None
    assert api_client.post("/api/v1/auth/email-verify/", {"token": token}).status_code == 200


def test_password_reset_revokes_rotated_refresh_and_access(api_client, auth_client, mailoutbox, settings):
    from django.contrib.auth.tokens import default_token_generator
    from rest_framework_simplejwt.tokens import RefreshToken

    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    user = User.objects.create_user("alice@example.com", PASSWORD)
    old_refresh = str(RefreshToken.for_user(user))
    rotated = api_client.post("/api/v1/auth/refresh/", {"refresh": old_refresh}).data
    token = default_token_generator.make_token(user)
    response = api_client.post(
        "/api/v1/auth/password-reset/confirm/",
        {"user_id": str(user.pk), "token": token, "password": "another-strong-ticket-password-94!"},
    )
    assert response.status_code == 200, response.data
    assert api_client.post("/api/v1/auth/refresh/", {"refresh": rotated["refresh"]}).status_code == 401
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {rotated['access']}")
    assert api_client.get("/api/v1/me/").status_code == 401
    api_client.credentials()
    assert (
        api_client.post(
            "/api/v1/auth/password-reset/confirm/", {"user_id": str(user.pk), "token": token, "password": PASSWORD}
        ).status_code
        == 400
    )


def test_reset_request_does_not_reveal_account_existence(api_client, mailoutbox, settings):
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    User.objects.create_user("alice@example.com", PASSWORD)
    known = api_client.post("/api/v1/auth/password-reset/", {"email": "alice@example.com"})
    unknown = api_client.post("/api/v1/auth/password-reset/", {"email": "unknown@example.com"})
    assert known.status_code == unknown.status_code == 202
    assert known.data == unknown.data
    from apps.notifications.services import process_outbox

    process_outbox()
    assert len(mailoutbox) == 1


def test_disabled_account_cannot_refresh(api_client):
    from rest_framework_simplejwt.tokens import RefreshToken

    user = User.objects.create_user("alice@example.com", PASSWORD)
    refresh = str(RefreshToken.for_user(user))
    user.is_active = False
    user.save()
    assert api_client.post("/api/v1/auth/refresh/", {"refresh": refresh}).status_code == 401
