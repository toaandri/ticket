from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.accounts.models import User
from apps.common.domain import Conflict, fingerprint, replay
from apps.events.models import Event
from apps.promotions.models import Promotion, PromotionRedemption
from apps.reservations.models import Reservation

from .models import Order, OrderItem


@transaction.atomic
def create_order(*, actor, reservation_id, key, promotion_code=""):
    User.objects.select_for_update().get(pk=actor.pk)
    digest = fingerprint({"reservation_id": str(reservation_id), "promotion_code": promotion_code.strip().upper()})
    previous = replay(Order.objects.filter(user=actor, idempotency_key=key).first(), digest)
    if previous:
        return previous
    reference = get_object_or_404(Reservation, pk=reservation_id, user=actor)
    event = Event.objects.select_for_update().get(pk=reference.event_id)
    reservation = Reservation.objects.select_for_update().get(pk=reference.pk)
    if reservation.status != "ACTIVE" or timezone.now() >= reservation.expires_at or event.status != "PUBLISHED":
        raise Conflict("This reservation has expired or cannot be checked out.")
    if Order.objects.filter(reservation=reservation).exists():
        raise Conflict("This reservation already has an order. Use its original idempotency key.")
    items = list(reservation.items.select_related("ticket_type").order_by("id"))
    subtotal = sum(item.unit_price_minor * item.quantity for item in items)
    currency = items[0].currency
    promotion = None
    discount = 0
    if promotion_code:
        promotion = (
            Promotion.objects.select_for_update()
            .filter(organization_id=event.organization_id, code=promotion_code.strip().upper(), active=True)
            .first()
        )
        if (
            not promotion
            or (promotion.event_id and promotion.event_id != event.pk)
            or not promotion.start_at <= timezone.now() < promotion.end_at
            or promotion.currency != currency
        ):
            raise ValidationError("This promotion is unavailable for this event.")
        redemptions = promotion.redemptions.exclude(order__status__in=["FAILED", "EXPIRED", "CANCELLED"])
        if (
            redemptions.count() >= promotion.usage_limit
            or redemptions.filter(user=actor).count() >= promotion.per_user_limit
        ):
            raise Conflict("Promotion usage limit reached.")
        discount = min(
            subtotal, subtotal * promotion.amount // 100 if promotion.kind == "PERCENT" else promotion.amount
        )
    order = Order.objects.create(
        user=actor,
        event=event,
        reservation=reservation,
        subtotal_minor=subtotal,
        discount_minor=discount,
        total_minor=subtotal - discount,
        currency=currency,
        expires_at=reservation.expires_at,
        idempotency_key=key,
        fingerprint=digest,
    )
    # Cumulative integer allocation preserves every minor unit without float rounding.
    cumulative = 0
    allocated = 0
    for item in items:
        amount = item.unit_price_minor * item.quantity
        cumulative += amount
        new_allocated = cumulative * discount // subtotal if subtotal else 0
        item_discount = new_allocated - allocated
        allocated = new_allocated
        OrderItem.objects.create(
            order=order,
            ticket_type=item.ticket_type,
            reservation_item=item,
            event_seat=item.event_seat,
            quantity=item.quantity,
            name=item.ticket_type.name,
            unit_price_minor=item.unit_price_minor,
            discount_minor=item_discount,
            total_minor=amount - item_discount,
        )
    if promotion:
        PromotionRedemption.objects.create(promotion=promotion, order=order, user=actor, amount_minor=discount)
    # Reservation remains ACTIVE and HELD until payment succeeds or its original deadline expires.
    return order
