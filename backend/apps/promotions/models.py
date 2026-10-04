from typing import ClassVar

from django.conf import settings
from django.db import models

from apps.common.domain import Entity


class Promotion(Entity):
    organization = models.ForeignKey("organizations.Organization", on_delete=models.PROTECT, related_name="promotions")
    event = models.ForeignKey("events.Event", on_delete=models.PROTECT, null=True, blank=True)
    code = models.CharField(max_length=40)
    kind = models.CharField(max_length=7, choices=[("PERCENT", "Percent"), ("FIXED", "Fixed minor units")])
    amount = models.PositiveIntegerField()
    currency = models.CharField(max_length=3, default="EUR")
    usage_limit = models.PositiveIntegerField(default=100)
    per_user_limit = models.PositiveSmallIntegerField(default=1)
    start_at = models.DateTimeField()
    end_at = models.DateTimeField()
    active = models.BooleanField(default=True)

    class Meta:
        constraints: ClassVar[list] = [
            models.UniqueConstraint(fields=["organization", "code"], name="unique_promotion_code"),
            models.CheckConstraint(condition=models.Q(start_at__lt=models.F("end_at")), name="promotion_time_order"),
            models.CheckConstraint(
                condition=models.Q(kind="FIXED") | models.Q(kind="PERCENT", amount__lte=100),
                name="promotion_valid_amount",
            ),
            models.CheckConstraint(
                condition=models.Q(usage_limit__gt=0, per_user_limit__gt=0), name="promotion_positive_limits"
            ),
        ]


class PromotionRedemption(Entity):
    promotion = models.ForeignKey(Promotion, on_delete=models.PROTECT, related_name="redemptions")
    order = models.OneToOneField("orders.Order", on_delete=models.PROTECT, related_name="promotion_redemption")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    amount_minor = models.PositiveIntegerField()
