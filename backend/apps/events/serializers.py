from typing import ClassVar

from rest_framework import serializers

from .models import Event, EventSeat, EventTicketType


class TicketTypeSerializer(serializers.ModelSerializer):
    section_id = serializers.UUIDField(read_only=True, allow_null=True)
    quota = serializers.IntegerField(min_value=1, max_value=100000)
    per_order_limit = serializers.IntegerField(min_value=1, max_value=20, default=10)
    currency = serializers.ChoiceField(choices=["EUR", "USD", "MGA"], default="EUR")

    class Meta:
        model = EventTicketType
        fields: ClassVar[list] = [
            "id",
            "code",
            "name",
            "kind",
            "price_minor",
            "currency",
            "quota",
            "per_order_limit",
            "section_id",
        ]
        read_only_fields: ClassVar[list] = ["id"]


class TicketTypeCreateSerializer(TicketTypeSerializer):
    venue_section_id = serializers.UUIDField(required=False, allow_null=True)

    class Meta(TicketTypeSerializer.Meta):
        fields: ClassVar[list] = [*TicketTypeSerializer.Meta.fields, "venue_section_id"]


class EventSerializer(serializers.ModelSerializer):
    organization_id = serializers.UUIDField(read_only=True)
    venue_id = serializers.UUIDField(required=False, allow_null=True)
    venue_name = serializers.CharField(source="venue.name", read_only=True, default="Online / to be announced")
    city = serializers.CharField(source="venue.city", read_only=True, default="Online")
    ticket_types = TicketTypeSerializer(many=True, read_only=True)

    class Meta:
        model = Event
        fields: ClassVar[list] = [
            "id",
            "organization_id",
            "venue_id",
            "venue_name",
            "city",
            "slug",
            "title",
            "description",
            "category",
            "start_at",
            "end_at",
            "event_timezone",
            "status",
            "seating_mode",
            "sales_start_at",
            "sales_end_at",
            "age_policy",
            "cancellation_policy",
            "published_at",
            "version",
            "ticket_types",
        ]
        read_only_fields: ClassVar[list] = ["id", "status", "published_at", "version"]


class EventCreateSerializer(EventSerializer):
    organization_id = serializers.UUIDField()


class EventSeatSerializer(serializers.ModelSerializer):
    label = serializers.CharField(source="seat.label")
    row_label = serializers.CharField(source="seat.row_label")
    accessible = serializers.BooleanField(source="seat.accessible")
    section_id = serializers.UUIDField(source="event_section_id")
    state = serializers.SerializerMethodField()

    class Meta:
        model = EventSeat
        fields: ClassVar[list] = ["id", "label", "row_label", "accessible", "section_id", "state"]

    def get_state(self, obj) -> str:
        from apps.inventory.models import SeatClaim

        try:
            return obj.claim.state
        except SeatClaim.DoesNotExist:
            return "AVAILABLE"


class BucketAvailabilitySerializer(serializers.Serializer):
    ticket_type_id = serializers.UUIDField()
    capacity = serializers.IntegerField()
    held = serializers.IntegerField()
    sold = serializers.IntegerField()
    available = serializers.IntegerField()


class AvailabilitySerializer(serializers.Serializer):
    event_id = serializers.UUIDField()
    version = serializers.IntegerField()
    ticket_types = BucketAvailabilitySerializer(many=True)
    seats = EventSeatSerializer(many=True)
