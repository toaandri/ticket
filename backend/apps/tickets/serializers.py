from rest_framework import serializers

from .models import Ticket
from .services import qr_url


class TicketSerializer(serializers.ModelSerializer):
    event_id = serializers.UUIDField()
    event_title = serializers.CharField(source="event.title")
    start_at = serializers.DateTimeField(source="event.start_at")
    ticket_type_name = serializers.CharField(source="ticket_type.name")
    seat_label = serializers.CharField(source="event_seat.seat.label", allow_null=True, default=None)
    qr_url = serializers.SerializerMethodField()
    order_id = serializers.UUIDField(source="order_item.order_id")

    class Meta:
        model = Ticket
        fields = (
            "id",
            "event_id",
            "event_title",
            "start_at",
            "ticket_type_name",
            "seat_label",
            "order_id",
            "public_code",
            "status",
            "qr_url",
            "created_at",
        )

    def get_qr_url(self, obj) -> str:
        return qr_url(obj)
