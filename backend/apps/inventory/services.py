from django.db import transaction

from apps.events.models import Event
from apps.inventory.models import InventoryBucket, SeatClaim
from apps.reservations.models import ReservationItem
from apps.tickets.models import Ticket


def _reconcile_event(event_id):
    """Read-only diagnostic. Never repair money/inventory by guessing."""
    mismatches = []
    for bucket in InventoryBucket.objects.filter(event_id=event_id).order_by("ticket_type_id"):
        expected_held = sum(
            ReservationItem.objects.filter(
                ticket_type_id=bucket.ticket_type_id, status="ACTIVE", reservation__status="ACTIVE"
            ).values_list("quantity", flat=True)
        )
        expected_sold = Ticket.objects.filter(ticket_type_id=bucket.ticket_type_id, inventory_released=False).count()
        if (bucket.held_count, bucket.sold_count) != (expected_held, expected_sold):
            mismatches.append(
                {
                    "bucket_id": str(bucket.pk),
                    "recorded_held": bucket.held_count,
                    "expected_held": expected_held,
                    "recorded_sold": bucket.sold_count,
                    "expected_sold": expected_sold,
                }
            )
    for claim in SeatClaim.objects.filter(event_id=event_id).select_related("reservation_item__reservation"):
        item = claim.reservation_item
        if (
            claim.event_id != item.reservation.event_id
            or claim.event_seat_id != item.event_seat_id
            or (claim.state == "HELD" and (item.status != "ACTIVE" or item.reservation.status != "ACTIVE"))
            or (
                claim.state == "SOLD"
                and not Ticket.objects.filter(event_seat_id=claim.event_seat_id, inventory_released=False).exists()
            )
        ):
            mismatches.append(
                {"claim_id": str(claim.pk), "problem": "Claim lifecycle does not match its reservation/ticket."}
            )
    for item in ReservationItem.objects.filter(
        reservation__event_id=event_id, event_seat__isnull=False, status="ACTIVE", reservation__status="ACTIVE"
    ):
        if not SeatClaim.objects.filter(reservation_item=item, state="HELD").exists():
            mismatches.append({"item_id": str(item.pk), "problem": "Assigned hold has no exclusive claim."})
    return mismatches


def reconcile_inventory():
    """Check each event under the same lock as writers for a consistent diagnostic."""
    mismatches = []
    for event_id in Event.objects.order_by("id").values_list("id", flat=True):
        with transaction.atomic():
            Event.objects.select_for_update().get(pk=event_id)
            mismatches.extend(_reconcile_event(event_id))
    return mismatches
