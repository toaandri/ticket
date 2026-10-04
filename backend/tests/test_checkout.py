import hashlib
import hmac
import json
import time
from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.accounts.models import User
from apps.checkins.models import CheckIn
from apps.checkins.services import check_in
from apps.common.domain import Conflict
from apps.inventory.models import InventoryBucket
from apps.orders.models import Order
from apps.orders.services import create_order
from apps.organizations.models import EventStaffAssignment, Membership
from apps.payments.models import PaymentAttempt, Refund
from apps.payments.providers.stripe_test import StripeTestPaymentProvider
from apps.payments.services import initiate_payment, process_payment_event, reconcile_payments, refund_order
from apps.promotions.models import Promotion
from apps.reservations.models import Reservation
from apps.reservations.services import create_hold, expire_holds
from apps.tickets.models import Ticket
from apps.tickets.services import qr_url, ticket_pdf, ticket_secret
from tests.test_inventory import ga_hold, parallel_requests


@pytest.fixture
def checkout_demo(inventory_demo):
    owner, _, _, event, ga, _ = inventory_demo
    hold = ga_hold(owner, event, ga, quantity=3)
    order = create_order(actor=owner, reservation_id=hold.pk, key="checkout")
    return owner, event, ga, hold, order


@pytest.mark.django_db
def test_checkout_replay_and_money_snapshots(checkout_demo):
    user, _, _, hold, order = checkout_demo
    assert create_order(actor=user, reservation_id=hold.pk, key="checkout").pk == order.pk
    with pytest.raises(Conflict):
        create_order(actor=user, reservation_id=hold.pk, key="another-key")
    with pytest.raises(Conflict):
        create_order(actor=user, reservation_id=hold.pk, key="checkout", promotion_code="NEW")
    assert order.total_minor == order.subtotal_minor == 3150
    order.total_minor = 1
    with pytest.raises(ValueError):
        order.save()
    with pytest.raises(ValueError):
        Order.objects.filter(pk=order.pk).update(total_minor=1)
    with pytest.raises(ValueError):
        order.delete()


@pytest.mark.django_db
def test_promotion_exact_allocation_and_limits(inventory_demo):
    owner, org, _, event, ga, assigned = inventory_demo
    now = timezone.now()
    Promotion.objects.create(
        organization=org,
        event=event,
        code="SAVE33",
        kind="PERCENT",
        amount=33,
        currency="EUR",
        usage_limit=1,
        per_user_limit=1,
        start_at=now - timedelta(days=1),
        end_at=now + timedelta(days=1),
    )
    hold = create_hold(
        actor=owner,
        event_id=event.pk,
        key="mixed",
        items=[
            {"ticket_type_id": str(ga.pk), "quantity": 3},
            {"ticket_type_id": str(assigned.pk), "event_seat_id": str(event.seats.first().pk), "quantity": 1},
        ],
    )
    order = create_order(actor=owner, reservation_id=hold.pk, key="promo", promotion_code="save33")
    assert order.discount_minor == 1699
    assert sum(order.items.values_list("discount_minor", flat=True)) == 1699
    assert sum(order.items.values_list("total_minor", flat=True)) == order.total_minor
    another = ga_hold(owner, event, ga, key="second")
    with pytest.raises(Conflict):
        create_order(actor=owner, reservation_id=another.pk, key="second", promotion_code="SAVE33")
    payment = initiate_payment(actor=owner, order_id=order.pk, key="pay")
    assert payment.status == "SUCCEEDED"
    assert Ticket.objects.count() == 4
    assert sum(Ticket.objects.values_list("admission_price_minor", flat=True)) == order.total_minor


@pytest.mark.django_db
def test_success_replays_issue_once(checkout_demo):
    user, event, ga, hold, order = checkout_demo
    payment = initiate_payment(actor=user, order_id=order.pk, key="pay")
    assert initiate_payment(actor=user, order_id=order.pk, key="pay").pk == payment.pk
    for _n in range(10):
        process_payment_event(
            payment_id=payment.pk, provider_event_id="provider-event", status="SUCCEEDED", amount=3150, currency="EUR"
        )
    assert Ticket.objects.count() == 3
    assert Ticket.objects.values("admission_index").distinct().count() == 3
    hold.refresh_from_db()
    order.refresh_from_db()
    bucket = InventoryBucket.objects.get(ticket_type=ga)
    assert hold.status == "CONSUMED" and order.status == "PAID"
    assert (bucket.held_count, bucket.sold_count) == (0, 3)
    assert event.tickets.count() == 3


@pytest.mark.django_db
def test_decline_releases_once_and_out_of_order_failure_ignored(checkout_demo):
    user, _, ga, hold, order = checkout_demo
    payment = initiate_payment(actor=user, order_id=order.pk, key="decline", scenario="decline")
    assert payment.status == "FAILED"
    assert not Ticket.objects.exists()
    hold.refresh_from_db()
    order.refresh_from_db()
    assert hold.status == "CANCELLED" and order.status == "FAILED"
    assert InventoryBucket.objects.get(ticket_type=ga).held_count == 0
    with pytest.raises(Conflict):
        initiate_payment(actor=user, order_id=order.pk, key="retry")


@pytest.mark.django_db
def test_pending_expiry_and_late_success_compensates_without_tickets(checkout_demo):
    user, _, ga, hold, order = checkout_demo
    payment = initiate_payment(actor=user, order_id=order.pk, key="pending", scenario="delayed")
    assert payment.status == "PENDING"
    now = timezone.now() - timedelta(seconds=1)
    Reservation.objects.filter(pk=hold.pk).update(expires_at=now)
    Order.objects.filter(pk=order.pk).update(expires_at=now)
    expire_holds()
    expire_holds()
    process_payment_event(
        payment_id=payment.pk, provider_event_id="late", status="SUCCEEDED", amount=3150, currency="EUR"
    )
    assert not Ticket.objects.exists()
    reconcile_payments()
    reconcile_payments()
    refund = Refund.objects.get()
    assert refund.status == "SUCCEEDED" and refund.amount_minor == 3150
    order.refresh_from_db()
    assert order.status == "EXPIRED"
    assert InventoryBucket.objects.get(ticket_type=ga).held_count == 0


@pytest.mark.django_db
def test_payment_amount_currency_mismatch_rolls_back(checkout_demo):
    user, _, _, _, order = checkout_demo
    payment = initiate_payment(actor=user, order_id=order.pk, key="pending", scenario="pending")
    with pytest.raises(ValidationError):
        process_payment_event(
            payment_id=payment.pk, provider_event_id="bad", status="SUCCEEDED", amount=999, currency="EUR"
        )
    assert not payment.paymenteventinbox_set.exists()
    assert not Ticket.objects.exists()
    process_payment_event(
        payment_id=payment.pk, provider_event_id="good", status="SUCCEEDED", amount=3150, currency="EUR"
    )
    process_payment_event(
        payment_id=payment.pk, provider_event_id="old-failure", status="FAILED", amount=3150, currency="EUR"
    )
    order.refresh_from_db()
    assert order.status == "PAID" and Ticket.objects.count() == 3


@pytest.mark.django_db
def test_partial_refund_allocation_and_replay(checkout_demo):
    user, _, ga, _, order = checkout_demo
    initiate_payment(actor=user, order_id=order.pk, key="pay")
    ticket = Ticket.objects.first()
    kwargs = {"actor": user, "order_id": order.pk, "ticket_ids": [ticket.pk], "reason": "Demo refund", "key": "refund"}
    refund = refund_order(**kwargs)
    assert refund_order(**kwargs).pk == refund.pk
    assert refund.amount_minor == 1050
    assert Refund.objects.count() == 1
    ticket.refresh_from_db()
    order.refresh_from_db()
    assert ticket.status == "REFUNDED" and order.status == "PARTIALLY_REFUNDED"
    assert InventoryBucket.objects.get(ticket_type=ga).sold_count == 2
    with pytest.raises(Conflict):
        refund_order(**{**kwargs, "key": "different"})


@pytest.mark.django_db
def test_tickets_secret_and_pdf_are_owner_scoped(checkout_demo, auth_client):
    user, _, _, _, order = checkout_demo
    initiate_payment(actor=user, order_id=order.pk, key="pay")
    ticket = Ticket.objects.select_related("event__venue", "ticket_type", "event_seat__seat").first()
    token = ticket_secret(ticket)
    assert len(token) == 43 and ticket.token_hash == hashlib.sha256(token.encode()).hexdigest()
    assert token not in str(ticket.__dict__)
    assert qr_url(ticket).endswith(token)
    assert ticket_pdf(ticket).startswith(b"%PDF")
    client = auth_client(user)
    assert client.get(f"/api/v1/tickets/{ticket.pk}/pdf/").status_code == 200
    assert client.get(f"/api/v1/tickets/{ticket.pk}/qr/").get("Content-Type") == "image/png"
    foreign = User.objects.create_user("foreign@example.com", "example-password-93!")
    assert auth_client(foreign).get(f"/api/v1/tickets/{ticket.pk}/").status_code == 404
    assert auth_client(foreign).get(f"/api/v1/orders/{order.pk}/").status_code == 404


def ready_gate(event):
    event.start_at = timezone.now() - timedelta(minutes=30)
    event.end_at = timezone.now() + timedelta(hours=2)
    event.save()


@pytest.mark.django_db
def test_gate_assignment_invalid_duplicate_revoked_and_closed(checkout_demo):
    owner, event, _, _, order = checkout_demo
    initiate_payment(actor=owner, order_id=order.pk, key="pay")
    ticket = Ticket.objects.first()
    scanner = User.objects.create_user("scanner@example.com", "example-password-93!")
    member = Membership.objects.create(user=scanner, organization=event.organization, role="SCANNER")
    with pytest.raises(PermissionDenied):
        check_in(actor=scanner, event_id=event.pk, token=ticket_secret(ticket), key="unassigned")
    EventStaffAssignment.objects.create(event=event, membership=member)
    assert check_in(actor=scanner, event_id=event.pk, token=ticket_secret(ticket), key="closed").result == "CLOSED"
    ready_gate(event)
    assert check_in(actor=scanner, event_id=event.pk, token="guess", key="invalid").result == "INVALID"
    scan = check_in(actor=scanner, event_id=event.pk, token=qr_url(ticket), key="accepted")
    assert scan.result == "ACCEPTED"
    assert check_in(actor=scanner, event_id=event.pk, token=qr_url(ticket), key="accepted").pk == scan.pk
    assert (
        check_in(actor=scanner, event_id=event.pk, token=ticket_secret(ticket), key="duplicate").result == "DUPLICATE"
    )
    other = Ticket.objects.exclude(pk=ticket.pk).first()
    other.status = "REVOKED"
    other.save()
    assert check_in(actor=scanner, event_id=event.pk, token=ticket_secret(other), key="revoked").result == "REVOKED"


@pytest.mark.django_db(transaction=True)
def test_two_scanners_exactly_one_accepted(checkout_demo):
    owner, event, _, _, order = checkout_demo
    initiate_payment(actor=owner, order_id=order.pk, key="pay")
    ready_gate(event)
    ticket = Ticket.objects.first()
    users = [owner, User.objects.create_user("manager@example.com", "example-password-93!")]
    Membership.objects.create(user=users[1], organization=event.organization, role="MANAGER")
    results = parallel_requests(
        users, lambda user: check_in(actor=user, event_id=event.pk, token=ticket_secret(ticket), key="scan").result, 2
    )
    assert sorted(results) == ["ACCEPTED", "DUPLICATE"]
    assert CheckIn.objects.filter(ticket=ticket, result="ACCEPTED").count() == 1


@pytest.mark.django_db(transaction=True)
def test_concurrent_duplicate_checkout_and_payment(checkout_demo):
    owner, _, _, hold, order = checkout_demo
    results = parallel_requests(
        [owner, owner], lambda user: create_order(actor=user, reservation_id=hold.pk, key="checkout").pk, 2
    )
    assert results[0] == results[1] == order.pk
    results = parallel_requests(
        [owner, owner], lambda user: initiate_payment(actor=user, order_id=order.pk, key="pay").pk, 2
    )
    assert results[0] == results[1]
    assert PaymentAttempt.objects.count() == 1 and Ticket.objects.count() == 3


def test_stripe_only_test_keys_and_signed_webhook(settings):
    settings.STRIPE_ENABLED = True
    settings.STRIPE_SECRET_KEY = "sk_live_fake"
    with pytest.raises(ValidationError):
        StripeTestPaymentProvider()
    settings.STRIPE_SECRET_KEY = "sk_test_fake"
    settings.STRIPE_WEBHOOK_SECRET = "whsec_synthetic"
    provider = StripeTestPaymentProvider()
    body = json.dumps({"id": "evt_test", "livemode": False, "type": "test"}).encode()
    timestamp = str(int(time.time()))
    signature = hmac.new(
        settings.STRIPE_WEBHOOK_SECRET.encode(), timestamp.encode() + b"." + body, "sha256"
    ).hexdigest()
    assert provider.verify_webhook(f"t={timestamp},v1={signature}", body)["id"] == "evt_test"
    with pytest.raises(PermissionDenied):
        provider.verify_webhook(f"t={timestamp},v1={signature}", body + b" ")
    with pytest.raises(PermissionDenied):
        provider.verify_webhook(f"t=1,v1={signature}", body)
