from typing import ClassVar

from rest_framework import serializers

from .models import Seat, Venue, VenueSection


class SeatSerializer(serializers.ModelSerializer):
    class Meta:
        model = Seat
        fields: ClassVar[list] = ["id", "row_label", "seat_number", "label", "accessible"]
        read_only_fields: ClassVar[list] = ["id"]


class SectionSerializer(serializers.ModelSerializer):
    seats = SeatSerializer(many=True, read_only=True)
    capacity = serializers.IntegerField(min_value=1, max_value=10000)

    class Meta:
        model = VenueSection
        fields: ClassVar[list] = ["id", "code", "name", "capacity", "seats"]
        read_only_fields: ClassVar[list] = ["id"]


class VenueSerializer(serializers.ModelSerializer):
    organization_id = serializers.UUIDField(read_only=True)
    sections = SectionSerializer(many=True, read_only=True)

    class Meta:
        model = Venue
        fields: ClassVar[list] = [
            "id",
            "organization_id",
            "name",
            "address",
            "city",
            "country_code",
            "timezone",
            "accessibility_info",
            "layout_frozen",
            "layout_version",
            "sections",
        ]
        read_only_fields: ClassVar[list] = ["id", "layout_frozen", "layout_version"]


class VenueCreateSerializer(VenueSerializer):
    organization_id = serializers.UUIDField()


class SeatsCreateSerializer(serializers.Serializer):
    section_id = serializers.UUIDField()
    seats = SeatSerializer(many=True, allow_empty=False, max_length=500)
