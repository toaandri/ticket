from typing import ClassVar

from django.db import models

from apps.common.domain import Entity


class Event(Entity):
    class Status(models.TextChoices):
        DRAFT = "DRAFT"
        PUBLISHED = "PUBLISHED"
        CANCELLED = "CANCELLED"
        COMPLETED = "COMPLETED"

    class Mode(models.TextChoices):
        GENERAL = "GENERAL"
        ASSIGNED = "ASSIGNED"
        MIXED = "MIXED"

    organization = models.ForeignKey("organizations.Organization", on_delete=models.PROTECT, related_name="events")
    venue = models.ForeignKey("venues.Venue", on_delete=models.PROTECT, related_name="events", null=True, blank=True)
    slug = models.SlugField()
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=50, default="Music", db_index=True)
    start_at = models.DateTimeField(db_index=True)
    end_at = models.DateTimeField()
    event_timezone = models.CharField(max_length=64, default="Indian/Antananarivo")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT, db_index=True)
    seating_mode = models.CharField(max_length=10, choices=Mode.choices, default=Mode.GENERAL)
    sales_start_at = models.DateTimeField()
    sales_end_at = models.DateTimeField()
    age_policy = models.CharField(max_length=200, default="All ages")
    cancellation_policy = models.TextField(
        default="Refunds before the event for unused tickets. Simulated payments only."
    )
    published_at = models.DateTimeField(null=True, blank=True)
    version = models.PositiveIntegerField(default=1)

    class Meta:
        ordering: ClassVar[list] = ["start_at", "id"]
        constraints: ClassVar[list] = [
            models.UniqueConstraint(fields=["organization", "slug"], name="unique_organization_event_slug"),
            models.CheckConstraint(condition=models.Q(start_at__lt=models.F("end_at")), name="event_time_order"),
            models.CheckConstraint(
                condition=models.Q(sales_start_at__lt=models.F("sales_end_at")), name="event_sales_time_order"
            ),
            models.CheckConstraint(
                condition=models.Q(status__in=["DRAFT", "PUBLISHED", "CANCELLED", "COMPLETED"]),
                name="event_valid_status",
            ),
            models.CheckConstraint(
                condition=models.Q(seating_mode__in=["GENERAL", "ASSIGNED", "MIXED"]), name="event_valid_mode"
            ),
        ]


class EventSection(Entity):
    event = models.ForeignKey(Event, on_delete=models.PROTECT, related_name="sections")
    venue_section = models.ForeignKey("venues.VenueSection", on_delete=models.PROTECT)
    capacity = models.PositiveIntegerField()
    layout_version = models.PositiveIntegerField()

    class Meta:
        constraints: ClassVar[list] = [
            models.UniqueConstraint(fields=["event", "venue_section"], name="unique_event_section")
        ]


class EventSeat(Entity):
    event = models.ForeignKey(Event, on_delete=models.PROTECT, related_name="seats")
    seat = models.ForeignKey("venues.Seat", on_delete=models.PROTECT)
    event_section = models.ForeignKey(EventSection, on_delete=models.PROTECT, related_name="seats")

    class Meta:
        constraints: ClassVar[list] = [models.UniqueConstraint(fields=["event", "seat"], name="unique_event_seat")]


class EventTicketType(Entity):
    event = models.ForeignKey(Event, on_delete=models.PROTECT, related_name="ticket_types")
    section = models.ForeignKey(
        EventSection, on_delete=models.PROTECT, null=True, blank=True, related_name="ticket_types"
    )
    code = models.SlugField()
    name = models.CharField(max_length=100)
    kind = models.CharField(max_length=8, choices=[("GENERAL", "General admission"), ("ASSIGNED", "Assigned seating")])
    price_minor = models.PositiveIntegerField()
    currency = models.CharField(max_length=3, default="EUR")
    quota = models.PositiveIntegerField()
    per_order_limit = models.PositiveSmallIntegerField(default=10)

    class Meta:
        constraints: ClassVar[list] = [
            models.UniqueConstraint(fields=["event", "code"], name="unique_event_ticket_code"),
            models.UniqueConstraint(
                fields=["section"], condition=models.Q(kind="ASSIGNED"), name="one_assigned_type_per_section"
            ),
            models.CheckConstraint(
                condition=models.Q(kind__in=["GENERAL", "ASSIGNED"]), name="ticket_type_valid_kind"
            ),
            models.CheckConstraint(
                condition=models.Q(currency__in=["EUR", "USD", "MGA"]), name="ticket_type_supported_currency"
            ),
            models.CheckConstraint(
                condition=models.Q(quota__gt=0, per_order_limit__gt=0, per_order_limit__lte=20),
                name="ticket_type_positive_limits",
            ),
        ]
