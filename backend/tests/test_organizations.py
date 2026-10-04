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
    response = auth_client(alice).post("/api/v1/organizations/", {"name": "Demo", "slug": "demo", "owner": str(bob.pk)})
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
