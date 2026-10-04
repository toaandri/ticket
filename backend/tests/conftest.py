"""PostgreSQL integration fixtures; pytest-django manages database creation."""

from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User
from apps.events.services import configure_ticket_type, create_event, publish_event
from apps.organizations.services import create_organization
from apps.venues.services import add_seats, add_section, create_venue


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


@pytest.fixture
def inventory_demo(db, settings):
    settings.DEBUG = True
    owner = User.objects.create_user("owner@example.com", "example-password-93!", email_verified_at=timezone.now())
    org = create_organization(owner=owner, name="Synthetic demo", slug="demo")
    venue = create_venue(actor=owner, organization_id=org.pk, name="Demo Hall", city="Antananarivo")
    section = add_section(actor=owner, venue_id=venue.pk, code="a", name="Section A", capacity=2)
    add_seats(
        actor=owner,
        venue_id=venue.pk,
        section_id=section.pk,
        seats=[{"row_label": "A", "seat_number": n, "label": f"A{n}", "accessible": n == 1} for n in [1, 2]],
    )
    now = timezone.now()
    event = create_event(
        actor=owner,
        organization_id=org.pk,
        venue_id=venue.pk,
        slug="concert",
        title="Synthetic Concert",
        start_at=now + timedelta(days=3),
        end_at=now + timedelta(days=3, hours=3),
        sales_start_at=now - timedelta(days=1),
        sales_end_at=now + timedelta(days=2),
        seating_mode="MIXED",
    )
    ga = configure_ticket_type(
        actor=owner,
        event_id=event.pk,
        code="ga",
        name="Standing",
        kind="GENERAL",
        price_minor=1050,
        currency="EUR",
        quota=20,
        per_order_limit=20,
    )
    assigned = configure_ticket_type(
        actor=owner,
        event_id=event.pk,
        code="reserved",
        name="Reserved",
        kind="ASSIGNED",
        price_minor=2000,
        currency="EUR",
        quota=2,
        per_order_limit=2,
        venue_section_id=section.pk,
    )
    publish_event(actor=owner, event_id=event.pk)
    return owner, org, venue, event, ga, assigned
