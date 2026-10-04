from typing import ClassVar

from django.conf import settings
from django.db import models

from apps.common.domain import Entity
from apps.orders.models import FinancialQuerySet, reference


class Ticket(Entity):
    order_item = models.ForeignKey("orders.OrderItem", on_delete=models.PROTECT, related_name="tickets")
    admission_index = models.PositiveSmallIntegerField()
    admission_price_minor = models.PositiveIntegerField()
    event = models.ForeignKey("events.Event", on_delete=models.PROTECT, related_name="tickets")
    holder = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="tickets")
    ticket_type = models.ForeignKey("events.EventTicketType", on_delete=models.PROTECT)
    event_seat = models.ForeignKey("events.EventSeat", on_delete=models.PROTECT, null=True)
    token_hash = models.CharField(max_length=64, unique=True)
    public_code = models.CharField(max_length=24, default=reference, unique=True)
    status = models.CharField(
        max_length=10, default="VALID", choices=[(s, s.title()) for s in ["VALID", "USED", "REVOKED", "REFUNDED"]]
    )
    used_at = models.DateTimeField(null=True)
    revoked_at = models.DateTimeField(null=True)
    version = models.PositiveIntegerField(default=1)
    refund = models.ForeignKey("payments.Refund", on_delete=models.PROTECT, null=True, related_name="tickets")
    objects = FinancialQuerySet.as_manager()

    class Meta:
        ordering = ("-created_at", "id")
        constraints: ClassVar[list] = [
            models.UniqueConstraint(fields=["order_item", "admission_index"], name="one_ticket_per_admission")
        ]
        indexes: ClassVar[list] = [models.Index(fields=["event", "status"])]
