from collections import Counter
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.accounts.models import User
from apps.common.domain import Conflict, fingerprint, replay
from apps.events.models import Event, EventSeat
from apps.inventory.models import InventoryBucket, SeatClaim, SeatClaimHistory

from .models import Reservation, ReservationItem


def release_locked(reservation, status="EXPIRED"):
    """Caller owns the Event lock. Idempotent release of ACTIVE items only."""
    if reservation.status != "ACTIVE":
        return
    for item in reservation.items.select_related("ticket_type").order_by("ticket_type_id", "id"):
        if item.status != "ACTIVE":
            continue
        bucket = InventoryBucket.objects.select_for_update().get(ticket_type=item.ticket_type)
        bucket.held_count -= item.quantity
        bucket.version += 1
        bucket.save()
        if item.event_seat_id:
            SeatClaimHistory.objects.create(
                event_id=reservation.event_id,
                event_seat_id=item.event_seat_id,
                reservation_item=item,
                action="RELEASED",
            )
            SeatClaim.objects.filter(reservation_item=item, state="HELD").delete()
        item.status = "RELEASED"
        item.save(update_fields=["status"])
    reservation.status = status
    reservation.save(update_fields=["status"])
    from apps.orders.models import Order

    Order.objects.filter(reservation=reservation, status__in=["PENDING", "PAYMENT_PROCESSING"]).update(
        status="EXPIRED" if status == "EXPIRED" else "CANCELLED"
    )


def expire_event_locked(event):
    for reservation in (
        Reservation.objects.select_for_update()
        .filter(event=event, status="ACTIVE", expires_at__lte=timezone.now())
        .order_by("id")
    ):
        release_locked(reservation)


@transaction.atomic
def create_hold(*, actor, event_id, items, key):
    # Serializes the actor's idempotency namespace even across different events.
    user = User.objects.select_for_update().get(pk=actor.pk)
    if not user.email_verified_at:
        raise PermissionDenied("Verify your email before reserving tickets.")
    digest = fingerprint({"event_id": str(event_id), "items": items})
    existing = replay(Reservation.objects.filter(user=user, idempotency_key=key).first(), digest)
    if existing:
        return existing
    event = get_object_or_404(Event.objects.select_for_update(), pk=event_id)
    now = timezone.now()
    if event.status != "PUBLISHED" or not event.sales_start_at <= now < event.sales_end_at or now >= event.start_at:
        raise Conflict("Ticket sales are closed for this event.")
    expire_event_locked(event)
    if not items or len(items) > 20:
        raise ValidationError("Select between 1 and 20 ticket items.")
    active_quantity = sum(
        ReservationItem.objects.filter(
            reservation__user=user,
            reservation__event=event,
            reservation__status__in=["ACTIVE", "CONSUMED"],
            status__in=["ACTIVE", "CONSUMED"],
        ).values_list("quantity", flat=True)
    )
    total = sum(item["quantity"] for item in items)
    if total > 20 or active_quantity + total > 20:
        raise ValidationError("The event limit is 20 admissions per attendee.")
    types = {str(t.pk): t for t in event.ticket_types.select_related("section")}
    quantities = Counter()
    seats = set()
    prepared = []
    for entry in items:
        ticket_type = types.get(str(entry["ticket_type_id"]))
        if not ticket_type:
            raise ValidationError("Ticket type does not belong to this event.")
        quantity = entry["quantity"]
        if not 1 <= quantity <= 20:
            raise ValidationError("Invalid quantity.")
        quantities[ticket_type.pk] += quantity
        seat_id = entry.get("event_seat_id")
        seat = None
        if ticket_type.kind == "ASSIGNED":
            if not seat_id or quantity != 1 or str(seat_id) in seats:
                raise ValidationError("Choose each assigned seat once, with quantity 1.")
            seat = get_object_or_404(EventSeat, pk=seat_id, event=event, event_section=ticket_type.section)
            if SeatClaim.objects.filter(event_seat=seat).exists():
                raise Conflict("This seat is held or sold. Choose another seat.")
            seats.add(str(seat_id))
        elif seat_id:
            raise ValidationError("General admission does not take a numbered seat.")
        prepared.append((ticket_type, quantity, seat))
    buckets = {}
    for type_id, quantity in sorted(quantities.items(), key=lambda item: str(item[0])):
        ticket_type = types[str(type_id)]
        bucket = InventoryBucket.objects.select_for_update().get(ticket_type_id=type_id)
        if quantity > ticket_type.per_order_limit:
            raise ValidationError("Per-order ticket limit exceeded.")
        if bucket.capacity - bucket.held_count - bucket.sold_count < quantity:
            raise Conflict("There are not enough tickets available.")
        buckets[type_id] = bucket
    reservation = Reservation.objects.create(
        user=user,
        event=event,
        expires_at=min(now + timedelta(minutes=settings.RESERVATION_HOLD_MINUTES), event.sales_end_at),
        idempotency_key=key,
        fingerprint=digest,
    )
    for ticket_type, quantity, seat in prepared:
        item = ReservationItem.objects.create(
            reservation=reservation,
            ticket_type=ticket_type,
            event_seat=seat,
            quantity=quantity,
            unit_price_minor=ticket_type.price_minor,
            currency=ticket_type.currency,
        )
        if seat:
            SeatClaim.objects.create(
                event=event, event_seat=seat, reservation_item=item, expires_at=reservation.expires_at
            )
            SeatClaimHistory.objects.create(event=event, event_seat=seat, reservation_item=item, action="HELD")
    for type_id, bucket in buckets.items():
        bucket.held_count += quantities[type_id]
        bucket.version += 1
        bucket.save()
    event.version += 1
    event.save(update_fields=["version"])
    return reservation


@transaction.atomic
def cancel_hold(*, actor, reservation_id):
    reference = get_object_or_404(Reservation, pk=reservation_id, user=actor)
    Event.objects.select_for_update().get(pk=reference.event_id)
    reservation = Reservation.objects.select_for_update().get(pk=reference.pk)
    if reservation.status == "CONSUMED":
        raise Conflict("A paid reservation cannot be cancelled as a hold.")
    release_locked(reservation, "CANCELLED")
    return reservation


def expire_holds(batch_size=100):
    event_ids = list(
        Reservation.objects.filter(status="ACTIVE", expires_at__lte=timezone.now())
        .order_by("expires_at")
        .values_list("event_id", flat=True)[:batch_size]
    )
    for event_id in dict.fromkeys(event_ids):
        with transaction.atomic():
            event = Event.objects.select_for_update(skip_locked=True).filter(pk=event_id).first()
            if event:
                expire_event_locked(event)
    return len(event_ids)
