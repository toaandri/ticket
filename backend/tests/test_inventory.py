from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier

import pytest
from django.db import IntegrityError, close_old_connections, connection, transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.accounts.models import User
from apps.common.domain import Conflict
from apps.events.models import Event
from apps.events.services import configure_ticket_type, create_event, publish_event
from apps.inventory.models import InventoryBucket, SeatClaim
from apps.organizations.services import create_organization
from apps.reservations.models import Reservation
from apps.reservations.services import cancel_hold, create_hold, expire_holds
from apps.venues.services import add_seats, add_section, create_venue


@pytest.fixture
def inventory_demo(db):
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


def ga_hold(user, event, ga, quantity=1, key="hold-key"):
    return create_hold(
        actor=user, event_id=event.pk, items=[{"ticket_type_id": str(ga.pk), "quantity": quantity}], key=key
    )


@pytest.mark.django_db
def test_publish_freezes_layout_and_ticket_configuration(inventory_demo):
    owner, _, venue, event, _, _ = inventory_demo
    venue.refresh_from_db()
    assert venue.layout_frozen
    with pytest.raises(Conflict):
        add_section(actor=owner, venue_id=venue.pk, code="b", name="New", capacity=10)
    with pytest.raises(Conflict):
        configure_ticket_type(
            actor=owner,
            event_id=event.pk,
            code="other",
            name="Other",
            kind="GENERAL",
            price_minor=100,
            currency="EUR",
            quota=10,
        )
    assert publish_event(actor=owner, event_id=event.pk).id == event.id


@pytest.mark.django_db
def test_invalid_publish_times_and_cross_tenant_venue(inventory_demo):
    owner, org, venue, event, _, _ = inventory_demo
    event.status = "DRAFT"
    event.ticket_types.all().update(kind="GENERAL")
    event.save()
    with pytest.raises(ValidationError):
        publish_event(actor=owner, event_id=event.pk)
    other = User.objects.create_user("other@example.com", "example-password-93!")
    foreign = create_organization(owner=other, name="Other", slug="other")
    from django.http import Http404

    with pytest.raises(Http404):
        create_event(actor=other, organization_id=foreign.pk, venue_id=venue.pk)
    with pytest.raises(IntegrityError), transaction.atomic():
        Event.objects.filter(pk=event.pk).update(end_at=event.start_at)
    assert org.events.count() == 1


@pytest.mark.django_db
def test_hold_replay_payload_conflict_and_price_snapshot(inventory_demo):
    user, _, _, event, ga, _ = inventory_demo
    hold = ga_hold(user, event, ga, quantity=2)
    assert ga_hold(user, event, ga, quantity=2).pk == hold.pk
    with pytest.raises(Conflict):
        ga_hold(user, event, ga, quantity=3)
    ga.price_minor = 9999
    ga.save()
    assert hold.items.get().unit_price_minor == 1050
    bucket = InventoryBucket.objects.get(ticket_type=ga)
    assert bucket.held_count == 2


@pytest.mark.django_db
def test_expiry_releases_inventory_exactly_once_and_seat_reusable(inventory_demo):
    user, _, _, event, ga, assigned = inventory_demo
    seat = event.seats.first()
    hold = create_hold(
        actor=user,
        event_id=event.pk,
        key="seat",
        items=[
            {"ticket_type_id": str(assigned.pk), "event_seat_id": str(seat.pk), "quantity": 1},
            {"ticket_type_id": str(ga.pk), "quantity": 3},
        ],
    )
    with pytest.raises(Conflict):
        create_hold(
            actor=user,
            event_id=event.pk,
            key="occupied",
            items=[{"ticket_type_id": str(assigned.pk), "event_seat_id": str(seat.pk), "quantity": 1}],
        )
    Reservation.objects.filter(pk=hold.pk).update(expires_at=timezone.now() - timedelta(seconds=1))
    expire_holds()
    expire_holds()
    hold.refresh_from_db()
    assert hold.status == "EXPIRED"
    assert not SeatClaim.objects.exists()
    assert list(event.inventory.values_list("held_count", flat=True)) == [0, 0]
    create_hold(
        actor=user,
        event_id=event.pk,
        key="new-seat",
        items=[{"ticket_type_id": str(assigned.pk), "event_seat_id": str(seat.pk), "quantity": 1}],
    )
    assert SeatClaim.objects.count() == 1


@pytest.mark.django_db
def test_cancel_twice_and_constraints(inventory_demo):
    user, _, _, event, ga, _ = inventory_demo
    hold = ga_hold(user, event, ga, quantity=2)
    cancel_hold(actor=user, reservation_id=hold.pk)
    cancel_hold(actor=user, reservation_id=hold.pk)
    bucket = ga.inventory
    bucket.refresh_from_db()
    assert bucket.held_count == 0
    with pytest.raises(IntegrityError), transaction.atomic():
        InventoryBucket.objects.filter(pk=bucket.pk).update(held_count=21)
    with pytest.raises(ValidationError):
        ga_hold(user, event, ga, quantity=21, key="too-many")


@pytest.mark.django_db
def test_unverified_and_closed_sales_and_wrong_seat_rejected(inventory_demo):
    user, _, _, event, ga, assigned = inventory_demo
    user.email_verified_at = None
    user.save()
    with pytest.raises(PermissionDenied):
        ga_hold(user, event, ga)
    user.email_verified_at = timezone.now()
    user.save()
    with pytest.raises(ValidationError):
        create_hold(
            actor=user, event_id=event.pk, key="bad-seat", items=[{"ticket_type_id": str(assigned.pk), "quantity": 2}]
        )
    with pytest.raises(ValidationError):
        create_hold(
            actor=user,
            event_id=event.pk,
            key="bad-ga",
            items=[{"ticket_type_id": str(ga.pk), "quantity": 1, "event_seat_id": str(event.seats.first().pk)}],
        )
    event.sales_end_at = timezone.now() - timedelta(seconds=1)
    event.save()
    with pytest.raises(Conflict):
        ga_hold(user, event, ga)


@pytest.mark.django_db
def test_public_discovery_and_private_writes(inventory_demo, api_client, auth_client):
    owner, org, venue, event, ga, _ = inventory_demo
    response = api_client.get("/api/v1/events/?search=Synthetic&city=Antananarivo")
    assert response.status_code == 200
    assert response.data["count"] == 1
    availability = api_client.get(f"/api/v1/events/{event.pk}/availability/")
    assert availability.status_code == 200
    assert len(availability.data["seats"]) == 2
    assert availability.data["seats"][0]["state"] == "AVAILABLE"
    outsider = User.objects.create_user(
        "outsider@example.com", "example-password-93!", email_verified_at=timezone.now()
    )
    client = auth_client(outsider)
    assert client.get(f"/api/v1/venues/{venue.pk}/").status_code == 404
    assert client.post(f"/api/v1/events/{event.pk}/publish/").status_code == 403
    hold = ga_hold(owner, event, ga)
    assert client.get(f"/api/v1/reservations/{hold.pk}/").status_code == 404
    payload = {"event_id": str(event.pk), "items": [{"ticket_type_id": str(ga.pk), "quantity": 1}]}
    assert client.post("/api/v1/reservations/", payload, format="json").status_code == 400
    response = client.post("/api/v1/reservations/", payload, format="json", HTTP_IDEMPOTENCY_KEY="api-hold")
    assert response.status_code == 201, response.data
    assert response.data["items"][0]["unit_price_minor"] == 1050
    assert str(org.pk) == str(event.organization_id)


def parallel_requests(users, operation, workers):
    assert connection.vendor == "postgresql", "Race tests must use real PostgreSQL"
    barrier = Barrier(workers)

    def run(user):
        close_old_connections()
        try:
            barrier.wait(timeout=30)
            try:
                return operation(user)
            except Conflict:
                return None
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(run, users))


@pytest.mark.django_db(transaction=True)
def test_two_buyers_one_seat_race(inventory_demo):
    _, _, _, event, _, assigned = inventory_demo
    users = [
        User.objects.create_user(f"buyer{n}@example.com", "example-password-93!", email_verified_at=timezone.now())
        for n in range(2)
    ]
    seat = event.seats.first()
    results = parallel_requests(
        users,
        lambda user: create_hold(
            actor=user,
            event_id=event.pk,
            key="race",
            items=[{"ticket_type_id": str(assigned.pk), "event_seat_id": str(seat.pk), "quantity": 1}],
        ).pk,
        2,
    )
    assert sum(result is not None for result in results) == 1
    assert SeatClaim.objects.count() == 1
    assert InventoryBucket.objects.get(ticket_type=assigned).held_count == 1


@pytest.mark.django_db(transaction=True)
def test_100_buyers_ga_20_race(inventory_demo):
    _, _, _, event, ga, _ = inventory_demo
    users = [
        User.objects.create_user(f"buyer{n}@example.com", "example-password-93!", email_verified_at=timezone.now())
        for n in range(100)
    ]
    # Batches of 20 simultaneous connections avoid exceeding a stock PostgreSQL
    # max_connections=100 while still forcing conflicts around the last units.
    results = []
    for offset in range(0, 100, 20):
        results.extend(parallel_requests(users[offset : offset + 20], lambda user: ga_hold(user, event, ga).pk, 20))
    bucket = InventoryBucket.objects.get(ticket_type=ga)
    assert sum(result is not None for result in results) == 20
    assert bucket.held_count == 20
    assert bucket.held_count + bucket.sold_count <= bucket.capacity
