from rest_framework import serializers

from apps.events.serializers import BucketAvailabilitySerializer


class MetricInventorySerializer(BucketAvailabilitySerializer):
    name = serializers.CharField()
    kind = serializers.CharField()


class DailySalesSerializer(serializers.Serializer):
    date = serializers.DateField()
    orders = serializers.IntegerField()
    gross_minor = serializers.IntegerField()


class EventMetricsSerializer(serializers.Serializer):
    event_id = serializers.UUIDField()
    currency = serializers.CharField()
    simulated = serializers.BooleanField()
    issued = serializers.IntegerField()
    active_tickets = serializers.IntegerField()
    refunded_tickets = serializers.IntegerField()
    gross_minor = serializers.IntegerField()
    refunds_minor = serializers.IntegerField()
    net_minor = serializers.IntegerField()
    accepted_checkins = serializers.IntegerField()
    checkin_rate_basis_points = serializers.IntegerField()
    inventory = MetricInventorySerializer(many=True)
    daily_sales = DailySalesSerializer(many=True)
