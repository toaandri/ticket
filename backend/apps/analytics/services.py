import csv
from collections import defaultdict
from io import StringIO
from zoneinfo import ZoneInfo

from apps.common.domain import require_role
from apps.orders.models import Order
from apps.payments.models import Refund
from apps.tickets.models import Ticket


def event_metrics(*, actor, event):
    require_role(actor, event.organization_id, ("OWNER", "MANAGER", "FINANCE"))
    orders = list(Order.objects.filter(event=event, paid_at__isnull=False))
    revenue = sum(order.total_minor for order in orders)
    refunds = sum(
        Refund.objects.filter(order__event=event, status="SUCCEEDED", order__paid_at__isnull=False).values_list(
            "amount_minor", flat=True
        )
    )
    tickets = Ticket.objects.filter(event=event)
    sold = tickets.count()
    refunded = tickets.filter(status="REFUNDED").count()
    checked_in = event.check_ins.filter(result="ACCEPTED").count()
    currencies = {order.currency for order in orders} | set(event.ticket_types.values_list("currency", flat=True))
    timeline = defaultdict(lambda: {"orders": 0, "gross_minor": 0})
    for order in orders:
        day = order.paid_at.astimezone(ZoneInfo(event.event_timezone)).date().isoformat()
        timeline[day]["orders"] += 1
        timeline[day]["gross_minor"] += order.total_minor
    breakdown = []
    for bucket in event.inventory.select_related("ticket_type").order_by("ticket_type__name"):
        breakdown.append(
            {
                "ticket_type_id": str(bucket.ticket_type_id),
                "name": bucket.ticket_type.name,
                "kind": bucket.ticket_type.kind,
                "capacity": bucket.capacity,
                "held": bucket.held_count,
                "sold": bucket.sold_count,
                "available": bucket.capacity - bucket.held_count - bucket.sold_count,
            }
        )
    return {
        "event_id": str(event.pk),
        "currency": next(iter(currencies), "EUR"),
        "simulated": True,
        "issued": sold,
        "active_tickets": tickets.filter(status__in=["VALID", "USED"]).count(),
        "refunded_tickets": refunded,
        "gross_minor": revenue,
        "refunds_minor": refunds,
        "net_minor": revenue - refunds,
        "accepted_checkins": checked_in,
        "checkin_rate_basis_points": checked_in * 10000 // (sold - refunded) if sold > refunded else 0,
        "inventory": breakdown,
        "daily_sales": [{"date": day, **values} for day, values in sorted(timeline.items())],
    }


def csv_cell(value):
    text = str(value)
    # Whitespace and control characters can hide formula prefixes in spreadsheets.
    return (
        "'" + text
        if text.lstrip(" \t\r\n").startswith(("=", "+", "-", "@")) or text.startswith(("\t", "\r", "\n"))
        else text
    )


def orders_csv(*, actor, event):
    require_role(actor, event.organization_id, ("OWNER", "MANAGER", "FINANCE"))
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["reference", "event", "status", "currency", "total_minor", "paid_at"])
    for order in event.orders.order_by("created_at"):
        writer.writerow(
            [
                csv_cell(value)
                for value in [
                    order.public_reference,
                    event.title,
                    order.status,
                    order.currency,
                    order.total_minor,
                    order.paid_at.isoformat() if order.paid_at else "",
                ]
            ]
        )
    return buffer.getvalue()
