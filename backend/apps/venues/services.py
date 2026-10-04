from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError

from apps.common.domain import Conflict, require_role
from apps.organizations.models import Organization

from .models import Seat, Venue, VenueSection


def validate_timezone(value):
    try:
        ZoneInfo(value)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ValidationError({"timezone": "Use an IANA timezone."}) from exc


@transaction.atomic
def create_venue(*, actor, organization_id, **data):
    organization = get_object_or_404(Organization.objects.select_for_update(), pk=organization_id)
    require_role(actor, organization.id)
    validate_timezone(data.get("timezone", "Indian/Antananarivo"))
    return Venue.objects.create(organization=organization, **data)


@transaction.atomic
def update_venue(*, actor, venue_id, data):
    venue = get_object_or_404(Venue.objects.select_for_update(), pk=venue_id)
    require_role(actor, venue.organization_id)
    if "timezone" in data:
        validate_timezone(data["timezone"])
    for key, value in data.items():
        setattr(venue, key, value)
    venue.save()
    return venue


@transaction.atomic
def add_section(*, actor, venue_id, code, name, capacity):
    venue = get_object_or_404(Venue.objects.select_for_update(), pk=venue_id)
    require_role(actor, venue.organization_id)
    if venue.layout_frozen:
        raise Conflict("This layout is frozen. Create a new venue layout instead.")
    if venue.sections.filter(code=code).exists():
        raise Conflict("Section code already exists.")
    section = VenueSection.objects.create(venue=venue, code=code, name=name, capacity=capacity)
    venue.layout_version += 1
    venue.save(update_fields=["layout_version"])
    return section


@transaction.atomic
def add_seats(*, actor, venue_id, section_id, seats):
    venue = get_object_or_404(Venue.objects.select_for_update(), pk=venue_id)
    require_role(actor, venue.organization_id)
    if venue.layout_frozen:
        raise Conflict("This layout is frozen.")
    section = get_object_or_404(VenueSection, pk=section_id, venue=venue)
    coordinates = {(s["row_label"], s["seat_number"]) for s in seats}
    if len(coordinates) != len(seats) or section.seats.count() + len(seats) > section.capacity:
        raise ValidationError("Duplicate seats or section capacity exceeded.")
    existing = set(section.seats.values_list("row_label", "seat_number"))
    if existing & coordinates:
        raise Conflict("Seat coordinates already exist.")
    created = Seat.objects.bulk_create([Seat(section=section, **s) for s in seats])
    venue.layout_version += 1
    venue.save(update_fields=["layout_version"])
    return created
