from typing import ClassVar

from django.conf import settings
from django.db import models

from apps.common.domain import Entity
from apps.orders.models import FinancialQuerySet


class PaymentAttempt(Entity):
    order = models.ForeignKey("orders.Order", on_delete=models.PROTECT, related_name="payments")
    provider = models.CharField(
        max_length=11, choices=[("MOCK", "Mock"), ("STRIPE_TEST", "Stripe test")], default="MOCK"
    )
    provider_payment_id = models.CharField(max_length=200, null=True, blank=True)
    idempotency_key = models.CharField(max_length=128)
    fingerprint = models.CharField(max_length=64)
    amount_minor = models.PositiveIntegerField()
    currency = models.CharField(max_length=3)
    status = models.CharField(
        max_length=10,
        default="CREATED",
        choices=[(s, s.title()) for s in ["CREATED", "PENDING", "SUCCEEDED", "FAILED", "CANCELLED", "REFUNDED"]],
    )
    checkout_url = models.URLField(blank=True, max_length=2000)
    payment_intent_id = models.CharField(max_length=200, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    objects = FinancialQuerySet.as_manager()

    class Meta:
        constraints: ClassVar[list] = [
            models.UniqueConstraint(fields=["order", "idempotency_key"], name="unique_order_payment_key"),
            models.UniqueConstraint(
                fields=["provider", "provider_payment_id"],
                condition=models.Q(provider_payment_id__isnull=False),
                name="unique_provider_payment",
            ),
            models.UniqueConstraint(
                fields=["order"],
                condition=models.Q(status__in=["CREATED", "PENDING", "SUCCEEDED"]),
                name="one_payable_attempt_per_order",
            ),
        ]


class PaymentEventInbox(Entity):
    provider = models.CharField(max_length=11)
    event_id = models.CharField(max_length=200)
    payload_digest = models.CharField(max_length=64)
    payment = models.ForeignKey(PaymentAttempt, on_delete=models.PROTECT)
    processed_at = models.DateTimeField(null=True)
    outcome = models.CharField(max_length=30, blank=True)
    objects = FinancialQuerySet.as_manager()

    class Meta:
        constraints: ClassVar[list] = [
            models.UniqueConstraint(fields=["provider", "event_id"], name="unique_payment_event")
        ]


class Refund(Entity):
    order = models.ForeignKey("orders.Order", on_delete=models.PROTECT, related_name="refunds")
    payment = models.ForeignKey(PaymentAttempt, on_delete=models.PROTECT, related_name="refunds")
    amount_minor = models.PositiveIntegerField()
    currency = models.CharField(max_length=3)
    reason = models.CharField(max_length=500)
    status = models.CharField(
        max_length=10,
        default="PENDING",
        choices=[("PENDING", "Pending"), ("SUCCEEDED", "Succeeded"), ("FAILED", "Failed")],
    )
    provider_ref = models.CharField(max_length=200, blank=True)
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True)
    completed_at = models.DateTimeField(null=True)
    idempotency_key = models.CharField(max_length=128)
    fingerprint = models.CharField(max_length=64)
    objects = FinancialQuerySet.as_manager()

    class Meta:
        constraints: ClassVar[list] = [
            models.UniqueConstraint(fields=["order", "idempotency_key"], name="unique_order_refund_key")
        ]
