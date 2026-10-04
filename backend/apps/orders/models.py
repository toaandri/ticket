import secrets
from typing import ClassVar

from django.conf import settings
from django.db import models

from apps.common.domain import Entity


def reference():
    return "TK-" + secrets.token_hex(8).upper()


MONEY_FIELDS = {"subtotal_minor", "discount_minor", "fees_minor", "tax_minor", "total_minor", "currency"}


class FinancialQuerySet(models.QuerySet):
    def delete(self):
        raise ValueError("Financial records cannot be deleted.")

    def update(self, **kwargs):
        if MONEY_FIELDS & kwargs.keys():
            raise ValueError("Order pricing snapshots are immutable.")
        return super().update(**kwargs)


class Order(Entity):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="orders")
    event = models.ForeignKey("events.Event", on_delete=models.PROTECT, related_name="orders")
    reservation = models.OneToOneField("reservations.Reservation", on_delete=models.PROTECT, related_name="order")
    public_reference = models.CharField(max_length=24, default=reference, unique=True)
    status = models.CharField(
        max_length=20,
        default="PENDING",
        choices=[
            (s, s.title())
            for s in [
                "PENDING",
                "PAYMENT_PROCESSING",
                "PAID",
                "FAILED",
                "EXPIRED",
                "CANCELLED",
                "PARTIALLY_REFUNDED",
                "REFUNDED",
            ]
        ],
    )
    subtotal_minor = models.PositiveIntegerField()
    discount_minor = models.PositiveIntegerField(default=0)
    fees_minor = models.PositiveIntegerField(default=0)
    tax_minor = models.PositiveIntegerField(default=0)
    total_minor = models.PositiveIntegerField()
    currency = models.CharField(max_length=3)
    expires_at = models.DateTimeField()
    paid_at = models.DateTimeField(null=True)
    idempotency_key = models.CharField(max_length=128)
    fingerprint = models.CharField(max_length=64)
    objects = FinancialQuerySet.as_manager()

    class Meta:
        ordering = ("-created_at", "id")
        constraints: ClassVar[list] = [
            models.UniqueConstraint(fields=["user", "idempotency_key"], name="unique_user_order_key"),
            models.CheckConstraint(
                check=models.Q(
                    total_minor=models.F("subtotal_minor")
                    - models.F("discount_minor")
                    + models.F("fees_minor")
                    + models.F("tax_minor")
                ),
                name="order_balanced_money",
            ),
            models.CheckConstraint(
                check=models.Q(discount_minor__lte=models.F("subtotal_minor")), name="order_discount_bound"
            ),
        ]
        indexes: ClassVar[list] = [
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["event", "status"]),
        ]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            previous = type(self).objects.filter(pk=self.pk).values(*MONEY_FIELDS).get()
            if any(previous[field] != getattr(self, field) for field in MONEY_FIELDS):
                raise ValueError("Order pricing snapshots are immutable.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("Financial records cannot be deleted.")


class OrderItem(Entity):
    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name="items")
    ticket_type = models.ForeignKey("events.EventTicketType", on_delete=models.PROTECT)
    reservation_item = models.OneToOneField("reservations.ReservationItem", on_delete=models.PROTECT)
    event_seat = models.ForeignKey("events.EventSeat", on_delete=models.PROTECT, null=True)
    quantity = models.PositiveSmallIntegerField()
    name = models.CharField(max_length=100)
    unit_price_minor = models.PositiveIntegerField()
    discount_minor = models.PositiveIntegerField(default=0)
    total_minor = models.PositiveIntegerField()
    objects = FinancialQuerySet.as_manager()

    class Meta:
        constraints: ClassVar[list] = [
            models.CheckConstraint(check=models.Q(quantity__gt=0), name="order_item_quantity_positive"),
            models.CheckConstraint(
                check=models.Q(
                    total_minor=models.F("quantity") * models.F("unit_price_minor") - models.F("discount_minor")
                ),
                name="order_item_balanced_money",
            ),
            models.UniqueConstraint(
                fields=["order", "event_seat"],
                condition=models.Q(event_seat__isnull=False),
                name="one_order_item_per_seat",
            ),
        ]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValueError("Order items are immutable.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("Order items cannot be deleted.")
