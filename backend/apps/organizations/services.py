from django.db import transaction

from .models import Membership, Organization


@transaction.atomic
def create_organization(*, owner, name, slug):
    organization = Organization.objects.create(owner=owner, name=name, slug=slug)
    Membership.objects.create(organization=organization, user=owner, role=Membership.Role.OWNER)
    return organization
