from typing import ClassVar

from django.conf import settings
from django.db import models

from apps.common.domain import Entity


class Reservation(Entity):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="reservations")
    event = models.ForeignKey("events.Event", on_delete=models.PROTECT, related_name="reservations")
    status = models.CharField(
        max_length=10,
        default="ACTIVE",
        choices=[(s, s.title()) for s in ["ACTIVE", "CONSUMED", "EXPIRED", "CANCELLED"]],
    )
    expires_at = models.DateTimeField(db_index=True)
    idempotency_key = models.CharField(max_length=128)
    fingerprint = models.CharField(max_length=64)

    class Meta:
        constraints: ClassVar[list] = [
            models.UniqueConstraint(fields=["user", "idempotency_key"], name="unique_user_hold_key")
        ]
        indexes: ClassVar[list] = [models.Index(fields=["event", "status", "expires_at"])]


class ReservationItem(Entity):
    reservation = models.ForeignKey(Reservation, on_delete=models.PROTECT, related_name="items")
    ticket_type = models.ForeignKey("events.EventTicketType", on_delete=models.PROTECT)
    event_seat = models.ForeignKey("events.EventSeat", on_delete=models.PROTECT, null=True, blank=True)
    quantity = models.PositiveSmallIntegerField()
    unit_price_minor = models.PositiveIntegerField()
    currency = models.CharField(max_length=3)
    status = models.CharField(
        max_length=8,
        default="ACTIVE",
        choices=[("ACTIVE", "Active"), ("CONSUMED", "Consumed"), ("RELEASED", "Released")],
    )

    class Meta:
        constraints: ClassVar[list] = [
            models.CheckConstraint(check=models.Q(quantity__gt=0), name="reservation_quantity_positive"),
            models.CheckConstraint(
                check=models.Q(event_seat__isnull=True) | models.Q(quantity=1), name="assigned_quantity_one"
            ),
            models.UniqueConstraint(
                fields=["reservation", "event_seat"],
                condition=models.Q(event_seat__isnull=False),
                name="one_seat_per_hold",
            ),
        ]
