from typing import ClassVar

from django.db import models

from apps.common.domain import Entity


class InventoryBucket(Entity):
    event = models.ForeignKey("events.Event", on_delete=models.PROTECT, related_name="inventory")
    ticket_type = models.OneToOneField("events.EventTicketType", on_delete=models.PROTECT, related_name="inventory")
    capacity = models.PositiveIntegerField()
    held_count = models.PositiveIntegerField(default=0)
    sold_count = models.PositiveIntegerField(default=0)
    version = models.PositiveIntegerField(default=1)

    class Meta:
        constraints: ClassVar[list] = [
            models.CheckConstraint(
                check=models.Q(capacity__gte=models.F("held_count") + models.F("sold_count")),
                name="inventory_within_capacity",
            )
        ]


class SeatClaim(Entity):
    event = models.ForeignKey("events.Event", on_delete=models.PROTECT)
    event_seat = models.OneToOneField("events.EventSeat", on_delete=models.PROTECT, related_name="claim")
    reservation_item = models.OneToOneField(
        "reservations.ReservationItem", on_delete=models.PROTECT, related_name="claim"
    )
    state = models.CharField(max_length=4, choices=[("HELD", "Held"), ("SOLD", "Sold")], default="HELD")
    expires_at = models.DateTimeField(null=True)

    class Meta:
        constraints: ClassVar[list] = [
            models.CheckConstraint(check=models.Q(state__in=["HELD", "SOLD"]), name="seat_claim_valid_state")
        ]


class SeatClaimHistory(Entity):
    event = models.ForeignKey("events.Event", on_delete=models.PROTECT)
    event_seat = models.ForeignKey("events.EventSeat", on_delete=models.PROTECT)
    reservation_item = models.ForeignKey("reservations.ReservationItem", on_delete=models.PROTECT)
    action = models.CharField(max_length=20)
