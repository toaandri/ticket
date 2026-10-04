from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.audit.models import AuditLog
from apps.common.domain import Conflict, require_role
from apps.inventory.models import InventoryBucket
from apps.organizations.models import Organization
from apps.venues.models import Venue
from apps.venues.services import validate_timezone

from .models import Event, EventSeat, EventSection, EventTicketType


def validate_event(data, existing=None):
    def value(key):
        return data.get(key, getattr(existing, key, None))

    if value("start_at") >= value("end_at"):
        raise ValidationError("Event start must precede its end.")
    if value("sales_start_at") >= value("sales_end_at") or value("sales_end_at") > value("end_at"):
        raise ValidationError("Invalid sales window.")
    validate_timezone(value("event_timezone") or "Indian/Antananarivo")


@transaction.atomic
def create_event(*, actor, organization_id, **data):
    organization = get_object_or_404(Organization.objects.select_for_update(), pk=organization_id)
    require_role(actor, organization.id)
    venue_id = data.pop("venue_id", None)
    venue = get_object_or_404(Venue, pk=venue_id, organization=organization) if venue_id else None
    validate_event(data)
    if organization.events.filter(slug=data["slug"]).exists():
        raise Conflict("Event slug already exists in this organization.")
    return Event.objects.create(organization=organization, venue=venue, **data)


@transaction.atomic
def update_event(*, actor, event_id, data):
    event = get_object_or_404(Event.objects.select_for_update(), pk=event_id)
    require_role(actor, event.organization_id)
    if event.status != "DRAFT":
        raise Conflict("Only drafts can be edited; cancel a published event through its cancellation workflow.")
    validate_event(data, event)
    if "slug" in data and event.organization.events.exclude(pk=event.pk).filter(slug=data["slug"]).exists():
        raise Conflict("Event slug already exists.")
    if "venue_id" in data:
        if event.sections.exists():
            raise Conflict("The venue cannot change after seating configuration.")
        venue_id = data.pop("venue_id")
        event.venue = (
            get_object_or_404(Venue, pk=venue_id, organization_id=event.organization_id) if venue_id else None
        )
    for key, value in data.items():
        setattr(event, key, value)
    event.version += 1
    event.save()
    return event


@transaction.atomic
def configure_ticket_type(*, actor, event_id, venue_section_id=None, **data):
    event = get_object_or_404(Event.objects.select_for_update(), pk=event_id)
    require_role(actor, event.organization_id)
    if event.status != "DRAFT":
        raise Conflict("Ticket configuration is frozen on publication.")
    if event.ticket_types.filter(code=data["code"]).exists():
        raise Conflict("Ticket type code already exists.")
    if event.ticket_types.exclude(currency=data["currency"]).exists():
        raise ValidationError("An event uses a single currency.")
    section = None
    if data["kind"] == "ASSIGNED":
        if event.seating_mode == "GENERAL" or not event.venue_id or not venue_section_id:
            raise ValidationError("Assigned tickets require a seating event, venue and section.")
        venue = Venue.objects.select_for_update().get(pk=event.venue_id)
        source = get_object_or_404(venue.sections, pk=venue_section_id)
        if event.sections.filter(venue_section=source, ticket_types__kind="ASSIGNED").exists():
            raise Conflict("A section has exactly one assigned ticket type.")
        if data["quota"] > source.seats.count():
            raise ValidationError("Assigned quota exceeds the numbered seats.")
        section, _ = EventSection.objects.get_or_create(
            event=event,
            venue_section=source,
            defaults={"capacity": source.capacity, "layout_version": venue.layout_version},
        )
        EventSeat.objects.bulk_create(
            [EventSeat(event=event, seat=seat, event_section=section) for seat in source.seats.all()],
            ignore_conflicts=True,
        )
    elif event.seating_mode == "ASSIGNED" or venue_section_id:
        raise ValidationError("General admission needs a GENERAL/MIXED event and no numbered section.")
    ticket_type = EventTicketType.objects.create(event=event, section=section, **data)
    InventoryBucket.objects.create(event=event, ticket_type=ticket_type, capacity=ticket_type.quota)
    return ticket_type


@transaction.atomic
def publish_event(*, actor, event_id):
    event = get_object_or_404(Event.objects.select_for_update(), pk=event_id)
    require_role(actor, event.organization_id)
    if event.organization.status != "ACTIVE":
        raise Conflict("This organization is suspended.")
    if event.status == "PUBLISHED":
        return event
    if event.status != "DRAFT":
        raise Conflict("This event cannot be published.")
    kinds = set(event.ticket_types.values_list("kind", flat=True))
    expected = (
        {"GENERAL"}
        if event.seating_mode == "GENERAL"
        else {"ASSIGNED"}
        if event.seating_mode == "ASSIGNED"
        else {"GENERAL", "ASSIGNED"}
    )
    if kinds != expected or event.start_at <= timezone.now() or event.sales_end_at <= timezone.now():
        raise ValidationError("Add valid ticket types and a future event/sales window before publication.")
    if event.venue_id:
        venue = Venue.objects.select_for_update().get(pk=event.venue_id)
        for section in event.sections.all():
            if section.layout_version != venue.layout_version:
                raise Conflict("The venue layout changed. Recreate the event seating configuration.")
        venue.layout_frozen = True
        venue.save(update_fields=["layout_frozen"])
    event.status = "PUBLISHED"
    event.published_at = timezone.now()
    event.version += 1
    event.save()
    AuditLog.objects.create(
        actor=actor,
        organization_id=event.organization_id,
        action="event.published",
        entity_type="Event",
        entity_id=event.pk,
    )
    return event


@transaction.atomic
def cancel_event(*, actor, event_id, platform_override=False, reason=""):
    from rest_framework.exceptions import PermissionDenied

    from apps.notifications.services import enqueue
    from apps.reservations.services import release_locked

    from .realtime import availability_changed

    event = get_object_or_404(Event.objects.select_for_update(), pk=event_id)
    if platform_override:
        if not actor.is_superuser:
            raise PermissionDenied("Platform administrator required.")
    else:
        require_role(actor, event.organization_id, ("OWNER", "MANAGER"))
    if event.status == "CANCELLED":
        return event
    if event.status == "COMPLETED":
        raise Conflict("A completed event cannot be cancelled.")
    event.status = "CANCELLED"
    event.version += 1
    event.save(update_fields=["status", "version"])
    for reservation in event.reservations.select_for_update().filter(status="ACTIVE").order_by("id"):
        release_locked(reservation, "CANCELLED")
    for order in event.orders.filter(paid_at__isnull=False):
        enqueue("event.cancelled", order.pk, key=f"cancelled:{order.pk}")
    AuditLog.objects.create(
        actor=actor,
        organization_id=event.organization_id,
        event=event,
        action="event.cancelled",
        entity_type="Event",
        entity_id=event.pk,
    )
    availability_changed(event)
    return event


def refund_cancelled_events(limit=100):
    from apps.orders.models import Order
    from apps.payments.services import refund_order
    from apps.tickets.models import Ticket

    for order in (
        Order.objects.filter(event__status="CANCELLED", status__in=["PAID", "PARTIALLY_REFUNDED"])
        .select_related("event__organization__owner")
        .order_by("created_at")[:limit]
    ):
        tickets = list(
            Ticket.objects.filter(order_item__order=order, status="VALID", refund__isnull=True).values_list(
                "id", flat=True
            )
        )
        if tickets:
            refund_order(
                actor=order.event.organization.owner,
                order_id=order.pk,
                ticket_ids=tickets,
                reason="Event cancellation",
                key=f"cancel-event:{order.pk}",
            )
