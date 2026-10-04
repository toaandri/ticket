from typing import ClassVar

from rest_framework import serializers

from .models import Reservation, ReservationItem


class HoldItemSerializer(serializers.Serializer):
    ticket_type_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1, max_value=20)
    event_seat_id = serializers.UUIDField(required=False, allow_null=True)


class HoldCreateSerializer(serializers.Serializer):
    event_id = serializers.UUIDField()
    items = HoldItemSerializer(many=True, allow_empty=False, max_length=20)


class ReservationItemSerializer(serializers.ModelSerializer):
    ticket_type_id = serializers.UUIDField()
    event_seat_id = serializers.UUIDField(allow_null=True)
    name = serializers.CharField(source="ticket_type.name")

    class Meta:
        model = ReservationItem
        fields: ClassVar[list] = [
            "id",
            "ticket_type_id",
            "event_seat_id",
            "quantity",
            "unit_price_minor",
            "currency",
            "status",
            "name",
        ]


class ReservationSerializer(serializers.ModelSerializer):
    event_id = serializers.UUIDField()
    items = ReservationItemSerializer(many=True)

    class Meta:
        model = Reservation
        fields: ClassVar[list] = ["id", "event_id", "status", "expires_at", "items"]
