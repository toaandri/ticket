from rest_framework import serializers

from .models import CheckIn


class CheckInCreateSerializer(serializers.Serializer):
    event_id = serializers.UUIDField()
    token = serializers.CharField(max_length=2000)
    device_id = serializers.CharField(required=False, allow_blank=True, max_length=100)


class CheckInSerializer(serializers.ModelSerializer):
    ticket_id = serializers.UUIDField(allow_null=True)
    event_id = serializers.UUIDField()

    class Meta:
        model = CheckIn
        fields = ("id", "ticket_id", "event_id", "result", "created_at")
