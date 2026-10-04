from typing import ClassVar

from django.conf import settings
from django.db import models

from apps.common.domain import Entity
from apps.orders.models import FinancialQuerySet


class CheckIn(Entity):
    ticket = models.ForeignKey("tickets.Ticket", on_delete=models.PROTECT, null=True, related_name="check_ins")
    event = models.ForeignKey("events.Event", on_delete=models.PROTECT, related_name="check_ins")
    scanned_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    result = models.CharField(
        max_length=11,
        choices=[(s, s.title()) for s in ["ACCEPTED", "DUPLICATE", "INVALID", "REVOKED", "WRONG_EVENT", "CLOSED"]],
    )
    device_id = models.CharField(max_length=100, blank=True)
    idempotency_key = models.CharField(max_length=128)
    fingerprint = models.CharField(max_length=64)
    objects = FinancialQuerySet.as_manager()

    class Meta:
        constraints: ClassVar[list] = [
            models.UniqueConstraint(
                fields=["ticket"], condition=models.Q(result="ACCEPTED"), name="one_accepted_check_in"
            ),
            models.UniqueConstraint(fields=["scanned_by", "idempotency_key"], name="unique_scanner_check_in_key"),
        ]
