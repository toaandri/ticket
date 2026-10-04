import pytest
from django.db import IntegrityError, transaction

from apps.accounts.models import User
from apps.organizations.models import Membership, Organization
from apps.organizations.services import create_organization

pytestmark = pytest.mark.django_db


def test_organization_creation_has_owner_membership(auth_client):
    user = User.objects.create_user("owner@example.com", "example-password-93!")
    response = auth_client(user).post("/api/v1/organizations/", {"name": "Demo", "slug": "demo"})
    assert response.status_code == 201, response.data
    membership = Membership.objects.get(organization_id=response.data["id"], user=user)
    assert membership.role == Membership.Role.OWNER


def test_foreign_organization_is_not_visible_even_to_platform_staff(auth_client):
    alice = User.objects.create_user("alice@example.com", "example-password-93!")
    bob = User.objects.create_superuser("bob@example.com", "example-password-93!")
    org = create_organization(owner=alice, name="Private", slug="private")
    client = auth_client(bob)
    assert client.get(f"/api/v1/organizations/{org.pk}/").status_code == 404
    assert client.get("/api/v1/organizations/").data["results"] == []


def test_client_cannot_set_other_user_as_owner(auth_client):
    alice = User.objects.create_user("alice@example.com", "example-password-93!")
    bob = User.objects.create_user("bob@example.com", "example-password-93!")
    response = auth_client(alice).post(
        "/api/v1/organizations/", {"name": "Demo", "slug": "demo", "owner": str(bob.pk)}
    )
    assert response.status_code == 201
    assert Organization.objects.get(pk=response.data["id"]).owner_id == alice.pk


def test_database_rejects_duplicate_membership_and_invalid_role():
    user = User.objects.create_user("owner@example.com", "example-password-93!")
    org = create_organization(owner=user, name="Demo", slug="demo")
    with pytest.raises(IntegrityError), transaction.atomic():
        Membership.objects.create(organization=org, user=user, role=Membership.Role.SCANNER)
    other = User.objects.create_user("other@example.com", "example-password-93!")
    with pytest.raises(IntegrityError), transaction.atomic():
        Membership.objects.create(organization=org, user=other, role="ADMIN")


def test_organization_creation_rolls_back_if_membership_fails(monkeypatch):
    user = User.objects.create_user("owner@example.com", "example-password-93!")

    def fail(*args, **kwargs):
        raise IntegrityError("forced membership failure")

    monkeypatch.setattr(Membership.objects, "create", fail)
    with pytest.raises(IntegrityError):
        create_organization(owner=user, name="Demo", slug="demo")
    assert not Organization.objects.exists()


def test_invitation_flow_requires_verified_matching_email_and_is_idempotent(auth_client, mailoutbox, settings):
    from django.utils import timezone

    from apps.audit.models import AuditLog
    from apps.organizations.models import Invitation

    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    owner = User.objects.create_user("owner@example.com", "example-password-93!")
    guest = User.objects.create_user("guest@example.com", "example-password-93!")
    wrong = User.objects.create_user("wrong@example.com", "example-password-93!", email_verified_at=timezone.now())
    org = create_organization(owner=owner, name="Demo", slug="demo")
    response = auth_client(owner).post(
        f"/api/v1/organizations/{org.pk}/invitations/", {"email": guest.email, "role": "SCANNER"}
    )
    assert response.status_code == 201, response.data
    from apps.notifications.services import process_outbox

    process_outbox()
    token = mailoutbox[0].body.splitlines()[-1]
    assert Invitation.objects.get().token_hash != token
    assert auth_client(wrong).post("/api/v1/invitations/accept/", {"token": token}).status_code == 403
    assert auth_client(guest).post("/api/v1/invitations/accept/", {"token": token}).status_code == 403
    guest.email_verified_at = timezone.now()
    guest.save()
    client = auth_client(guest)
    assert client.post("/api/v1/invitations/accept/", {"token": token}).status_code == 200
    assert client.post("/api/v1/invitations/accept/", {"token": token}).status_code == 200
    assert Membership.objects.filter(user=guest, organization=org).count() == 1
    assert AuditLog.objects.filter(action="invitation.accepted").count() == 1


def test_scanner_cannot_invite_or_change_roles(auth_client, settings):
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    owner = User.objects.create_user("owner@example.com", "example-password-93!")
    scanner = User.objects.create_user("scanner@example.com", "example-password-93!")
    org = create_organization(owner=owner, name="Demo", slug="demo")
    membership = Membership.objects.create(user=scanner, organization=org, role="SCANNER")
    client = auth_client(scanner)
    assert (
        client.post(
            f"/api/v1/organizations/{org.pk}/invitations/", {"email": "guest@example.com", "role": "MANAGER"}
        ).status_code
        == 403
    )
    assert (
        client.patch(f"/api/v1/organizations/{org.pk}/members/{membership.pk}/", {"role": "MANAGER"}).status_code
        == 403
    )
    membership.refresh_from_db()
    assert membership.role == "SCANNER"


def test_role_change_is_tenant_scoped_and_owner_cannot_be_demoted(auth_client):
    owner = User.objects.create_user("owner@example.com", "example-password-93!")
    other = User.objects.create_user("other@example.com", "example-password-93!")
    org = create_organization(owner=owner, name="Demo", slug="demo")
    foreign = create_organization(owner=other, name="Foreign", slug="foreign")
    membership = Membership.objects.get(organization=org, user=owner)
    client = auth_client(owner)
    assert (
        client.patch(f"/api/v1/organizations/{foreign.pk}/members/{membership.pk}/", {"role": "SCANNER"}).status_code
        == 404
    )
    assert (
        client.patch(f"/api/v1/organizations/{org.pk}/members/{membership.pk}/", {"role": "SCANNER"}).status_code
        == 403
    )


def test_audit_records_are_append_only():
    from apps.audit.models import AuditLog

    owner = User.objects.create_user("owner@example.com", "example-password-93!")
    create_organization(owner=owner, name="Demo", slug="demo")
    entry = AuditLog.objects.get()
    with pytest.raises(ValueError):
        AuditLog.objects.filter(pk=entry.pk).update(action="tampered")
    with pytest.raises(ValueError):
        entry.delete()
    with pytest.raises(ValueError):
        entry.save()
