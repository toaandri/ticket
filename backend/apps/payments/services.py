from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.audit.models import AuditLog
from apps.common.domain import Conflict, fingerprint, replay, require_role
from apps.events.models import Event
from apps.events.realtime import availability_changed
from apps.inventory.models import InventoryBucket, SeatClaim, SeatClaimHistory
from apps.notifications.services import enqueue
from apps.orders.models import Order
from apps.reservations.models import Reservation
from apps.reservations.services import release_locked
from apps.tickets.models import Ticket
from apps.tickets.services import issue_tickets_locked

from .models import PaymentAttempt, PaymentEventInbox, Refund
from .providers.mock import MockPaymentProvider


def provider_for(name):
    if name == "MOCK":
        return MockPaymentProvider()
    if name == "STRIPE_TEST":
        from .providers.stripe_test import StripeTestPaymentProvider

        return StripeTestPaymentProvider()
    raise ValidationError("Unknown payment provider.")


@transaction.atomic
def prepare_payment(*, actor, order_id, key, provider="MOCK", scenario="success"):
    reference = get_object_or_404(Order, pk=order_id, user=actor)
    event = Event.objects.select_for_update().get(pk=reference.event_id)
    reservation = Reservation.objects.select_for_update().get(pk=reference.reservation_id)
    order = Order.objects.select_for_update().get(pk=reference.pk)
    digest = fingerprint({"provider": provider, "scenario": scenario})
    existing = replay(order.payments.filter(idempotency_key=key).first(), digest)
    if existing:
        return existing, False
    if (
        order.status not in ["PENDING", "PAYMENT_PROCESSING"]
        or event.status != "PUBLISHED"
        or reservation.status != "ACTIVE"
        or timezone.now() >= order.expires_at
    ):
        raise Conflict("This order is no longer payable.")
    if provider == "MOCK" and scenario != "success" and not settings.DEBUG:
        raise PermissionDenied("Mock failure simulation is available only in development.")
    if scenario not in ["success", "decline", "pending", "timeout", "delayed"]:
        raise ValidationError("Unsupported mock scenario.")
    if order.payments.filter(status__in=["CREATED", "PENDING", "SUCCEEDED"]).exists():
        raise Conflict("A payment is already in progress. Reuse its idempotency key.")
    provider_for(provider)  # Validate configuration before recording an attempt.
    payment = PaymentAttempt.objects.create(
        order=order,
        provider=provider,
        idempotency_key=key,
        fingerprint=digest,
        amount_minor=order.total_minor,
        currency=order.currency,
    )
    order.status = "PAYMENT_PROCESSING"
    order.save(update_fields=["status"])
    return payment, True


def initiate_payment(*, actor, order_id, key, provider="MOCK", scenario="success"):
    payment, created = prepare_payment(actor=actor, order_id=order_id, key=key, provider=provider, scenario=scenario)
    if not created and payment.provider_payment_id:
        return payment
    # Remote calls are deliberately outside transactions; provider idempotency
    # is the payment UUID, so a crash before persistence can be retried safely.
    result = provider_for(provider).create_payment(payment, scenario)
    with transaction.atomic():
        Event.objects.select_for_update().get(pk=payment.order.event_id)
        current = PaymentAttempt.objects.select_for_update().get(pk=payment.pk)
        if not current.provider_payment_id:
            current.provider_payment_id = result.provider_id
            current.checkout_url = result.checkout_url
            current.status = "PENDING"
            current.save()
    if result.status in ["SUCCEEDED", "FAILED"]:
        process_payment_event(
            payment_id=payment.pk,
            provider_event_id=f"{payment.pk}:{result.status}",
            status=result.status,
            amount=payment.amount_minor,
            currency=payment.currency,
        )
    payment.refresh_from_db()
    return payment


@transaction.atomic
def process_payment_event(*, payment_id, provider_event_id, status, amount, currency, payment_intent_id=""):
    reference = get_object_or_404(PaymentAttempt.objects.select_related("order"), pk=payment_id)
    event = Event.objects.select_for_update().get(pk=reference.order.event_id)
    reservation = Reservation.objects.select_for_update().get(pk=reference.order.reservation_id)
    order = Order.objects.select_for_update().get(pk=reference.order_id)
    payment = PaymentAttempt.objects.select_for_update().get(pk=reference.pk)
    digest = fingerprint(
        {
            "payment": str(payment.pk),
            "status": status,
            "amount": amount,
            "currency": currency,
            "intent": payment_intent_id,
        }
    )
    inbox, created = PaymentEventInbox.objects.get_or_create(
        provider=payment.provider, event_id=provider_event_id, defaults={"payment": payment, "payload_digest": digest}
    )
    if not created:
        if inbox.payload_digest != digest or inbox.payment_id != payment.pk:
            raise Conflict("A provider event ID was reused with different data.")
        return payment
    if (
        amount != payment.amount_minor
        or currency.upper() != payment.currency
        or status not in ["SUCCEEDED", "FAILED", "PENDING"]
    ):
        raise ValidationError("Payment amount, currency or status mismatch.")
    if payment.status in ["SUCCEEDED", "REFUNDED"] or order.status in ["PAID", "PARTIALLY_REFUNDED", "REFUNDED"]:
        inbox.outcome = "IGNORED_FINAL"
    elif status == "SUCCEEDED":
        payment.status = "SUCCEEDED"
        payment.payment_intent_id = payment_intent_id
        if (
            reservation.status != "ACTIVE"
            or timezone.now() >= order.expires_at
            or event.status != "PUBLISHED"
            or order.status not in ["PENDING", "PAYMENT_PROCESSING"]
        ):
            release_locked(reservation)
            if order.status not in ["CANCELLED", "EXPIRED"]:
                order.status = "EXPIRED"
                order.save(update_fields=["status"])
            Refund.objects.get_or_create(
                order=order,
                idempotency_key=f"late:{payment.pk}",
                defaults={
                    "payment": payment,
                    "amount_minor": payment.amount_minor,
                    "currency": payment.currency,
                    "reason": "Automatic compensation for payment after checkout closed",
                    "fingerprint": digest,
                },
            )
            inbox.outcome = "LATE_COMPENSATION"
        else:
            for item in reservation.items.order_by("ticket_type_id", "id"):
                if item.status != "ACTIVE":
                    raise Conflict("Reservation inventory is no longer held.")
                bucket = InventoryBucket.objects.select_for_update().get(ticket_type=item.ticket_type)
                bucket.held_count -= item.quantity
                bucket.sold_count += item.quantity
                bucket.version += 1
                bucket.save()
                if item.event_seat_id:
                    claim = SeatClaim.objects.select_for_update().get(reservation_item=item, state="HELD")
                    claim.state = "SOLD"
                    claim.expires_at = None
                    claim.save()
                    SeatClaimHistory.objects.create(
                        event=event, event_seat_id=item.event_seat_id, reservation_item=item, action="SOLD"
                    )
                item.status = "CONSUMED"
                item.save(update_fields=["status"])
            reservation.status = "CONSUMED"
            reservation.save(update_fields=["status"])
            order.status = "PAID"
            order.paid_at = timezone.now()
            order.save(update_fields=["status", "paid_at"])
            issue_tickets_locked(order)
            enqueue("order.paid", order.pk, key=f"paid:{order.pk}")
            inbox.outcome = "PAID"
            AuditLog.objects.create(
                actor=order.user,
                organization_id=event.organization_id,
                action="order.paid",
                entity_type="Order",
                entity_id=order.pk,
            )
    elif status == "FAILED":
        payment.status = "FAILED"
        # Declines release immediately; a new reservation is needed for retry.
        release_locked(reservation, "CANCELLED")
        order.status = "FAILED"
        order.save(update_fields=["status"])
        inbox.outcome = "FAILED"
    else:
        payment.status = "PENDING"
        inbox.outcome = "PENDING"
    payment.save()
    inbox.processed_at = timezone.now()
    inbox.save()
    event.version += 1
    event.save(update_fields=["version"])
    availability_changed(event)
    return payment


@transaction.atomic
def prepare_refund(*, actor, order_id, ticket_ids, reason, key):
    reference = get_object_or_404(Order, pk=order_id)
    event = Event.objects.select_for_update().get(pk=reference.event_id)
    require_role(actor, event.organization_id, ("OWNER", "MANAGER"))
    order = Order.objects.select_for_update().get(pk=reference.pk)
    digest = fingerprint({"ticket_ids": sorted(str(value) for value in ticket_ids), "reason": reason})
    previous = replay(order.refunds.filter(idempotency_key=key).first(), digest)
    if previous:
        return previous
    if order.status not in ["PAID", "PARTIALLY_REFUNDED"] or (
        timezone.now() >= event.start_at and event.status != "CANCELLED"
    ):
        raise Conflict("Refunds are allowed for unused tickets before the event.")
    tickets = list(
        Ticket.objects.select_for_update().filter(order_item__order=order, pk__in=ticket_ids).order_by("id")
    )
    if (
        not ticket_ids
        or len(tickets) != len(ticket_ids)
        or any(ticket.status != "VALID" or ticket.refund_id for ticket in tickets)
    ):
        raise Conflict("Select unused, unrefunded tickets from this order.")
    payment = order.payments.get(status="SUCCEEDED")
    amount = sum(ticket.admission_price_minor for ticket in tickets)
    allocated = sum(order.refunds.exclude(status="FAILED").values_list("amount_minor", flat=True))
    if allocated + amount > payment.amount_minor:
        raise Conflict("Refund amount exceeds the remaining payment.")
    refund = Refund.objects.create(
        order=order,
        payment=payment,
        amount_minor=amount,
        currency=order.currency,
        reason=reason,
        requested_by=actor,
        idempotency_key=key,
        fingerprint=digest,
    )
    for ticket in tickets:
        # Revoke immediately, including while an external refund is pending.
        ticket.status = "REVOKED"
        ticket.revoked_at = timezone.now()
        ticket.refund = refund
        ticket.save()
    AuditLog.objects.create(
        actor=actor,
        organization_id=event.organization_id,
        action="refund.requested",
        entity_type="Refund",
        entity_id=refund.pk,
    )
    return refund


def complete_refund(refund):
    if refund.status == "SUCCEEDED":
        return refund
    provider_ref = provider_for(refund.payment.provider).refund(refund.payment, refund.amount_minor, str(refund.pk))
    with transaction.atomic():
        event = Event.objects.select_for_update().get(pk=refund.order.event_id)
        order = Order.objects.select_for_update().get(pk=refund.order_id)
        current = Refund.objects.select_for_update().get(pk=refund.pk)
        if current.status == "SUCCEEDED":
            return current
        for ticket in current.tickets.select_for_update().order_by("ticket_type_id", "id"):
            ticket.status = "REFUNDED"
            ticket.save(update_fields=["status"])
            # Resale is enabled only before the event and only if still published.
            if event.status == "PUBLISHED" and timezone.now() < event.start_at:
                bucket = InventoryBucket.objects.select_for_update().get(ticket_type=ticket.ticket_type)
                bucket.sold_count -= 1
                bucket.version += 1
                bucket.save()
                if ticket.event_seat_id:
                    claim = SeatClaim.objects.filter(event_seat_id=ticket.event_seat_id).first()
                    if claim:
                        SeatClaimHistory.objects.create(
                            event=event,
                            event_seat_id=ticket.event_seat_id,
                            reservation_item=claim.reservation_item,
                            action="REFUNDED",
                        )
                        claim.delete()
        current.status = "SUCCEEDED"
        current.provider_ref = provider_ref
        current.completed_at = timezone.now()
        current.save()
        remaining = Ticket.objects.filter(
            order_item__order=order, status__in=["VALID", "USED", "REVOKED"], refund__isnull=True
        ).exists()
        if order.paid_at:
            order.status = "PARTIALLY_REFUNDED" if remaining else "REFUNDED"
            order.save(update_fields=["status"])
        enqueue("order.refund", current.pk, key=f"refund:{current.pk}")
        event.version += 1
        event.save(update_fields=["version"])
        availability_changed(event)
        return current


def refund_order(**kwargs):
    return complete_refund(prepare_refund(**kwargs))


def reconcile_payments(limit=100):
    for payment in PaymentAttempt.objects.filter(status="PENDING").order_by("created_at")[:limit]:
        outcome = provider_for(payment.provider).fetch_status(payment)
        if outcome in ["SUCCEEDED", "FAILED"]:
            process_payment_event(
                payment_id=payment.pk,
                provider_event_id=f"reconcile:{payment.pk}:{outcome}",
                status=outcome,
                amount=payment.amount_minor,
                currency=payment.currency,
            )
    for refund in (
        Refund.objects.filter(status="PENDING").select_related("payment", "order").order_by("created_at")[:limit]
    ):
        complete_refund(refund)
