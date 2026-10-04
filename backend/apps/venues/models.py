from typing import ClassVar

from django.db import models

from apps.common.domain import Entity


class Venue(Entity):
    organization = models.ForeignKey("organizations.Organization", on_delete=models.PROTECT, related_name="venues")
    name = models.CharField(max_length=200)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100)
    country_code = models.CharField(max_length=2, default="MG")
    timezone = models.CharField(max_length=64, default="Indian/Antananarivo")
    accessibility_info = models.TextField(blank=True)
    layout_frozen = models.BooleanField(default=False)
    layout_version = models.PositiveIntegerField(default=1)


class VenueSection(Entity):
    venue = models.ForeignKey(Venue, on_delete=models.PROTECT, related_name="sections")
    code = models.SlugField()
    name = models.CharField(max_length=100)
    capacity = models.PositiveIntegerField()

    class Meta:
        constraints: ClassVar[list] = [models.UniqueConstraint(fields=["venue", "code"], name="unique_venue_section")]


class Seat(Entity):
    section = models.ForeignKey(VenueSection, on_delete=models.PROTECT, related_name="seats")
    row_label = models.CharField(max_length=20)
    seat_number = models.PositiveIntegerField()
    label = models.CharField(max_length=50)
    accessible = models.BooleanField(default=False)

    class Meta:
        ordering: ClassVar[list] = ["row_label", "seat_number"]
        constraints: ClassVar[list] = [
            models.UniqueConstraint(fields=["section", "row_label", "seat_number"], name="unique_seat_coordinates")
        ]
