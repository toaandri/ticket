from rest_framework import serializers

from apps.payments.models import PaymentAttempt, Refund

from .models import Order, OrderItem


class OrderCreateSerializer(serializers.Serializer):
    reservation_id = serializers.UUIDField()
    promotion_code = serializers.CharField(required=False, allow_blank=True, max_length=40)


class OrderItemSerializer(serializers.ModelSerializer):
    ticket_type_id = serializers.UUIDField()
    event_seat_id = serializers.UUIDField(allow_null=True)

    class Meta:
        model = OrderItem
        fields = (
            "id",
            "ticket_type_id",
            "event_seat_id",
            "quantity",
            "name",
            "unit_price_minor",
            "discount_minor",
            "total_minor",
        )


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentAttempt
        fields = ("id", "provider", "status", "amount_minor", "currency", "checkout_url", "created_at")


class RefundSerializer(serializers.ModelSerializer):
    class Meta:
        model = Refund
        fields = ("id", "status", "amount_minor", "currency", "reason", "created_at", "completed_at")


class OrderSerializer(serializers.ModelSerializer):
    event_id = serializers.UUIDField()
    event_title = serializers.CharField(source="event.title")
    items = OrderItemSerializer(many=True)
    payments = PaymentSerializer(many=True)
    refunds = RefundSerializer(many=True)

    class Meta:
        model = Order
        fields = (
            "id",
            "event_id",
            "event_title",
            "public_reference",
            "status",
            "subtotal_minor",
            "discount_minor",
            "fees_minor",
            "tax_minor",
            "total_minor",
            "currency",
            "expires_at",
            "paid_at",
            "created_at",
            "items",
            "payments",
            "refunds",
        )


class PaymentCreateSerializer(serializers.Serializer):
    provider = serializers.ChoiceField(choices=["MOCK", "STRIPE_TEST"], default="MOCK")
    scenario = serializers.ChoiceField(
        choices=["success", "decline", "pending", "timeout", "delayed"], default="success"
    )


class SimulationSerializer(serializers.Serializer):
    payment_id = serializers.UUIDField()
    outcome = serializers.ChoiceField(choices=["SUCCEEDED", "FAILED", "PENDING"])


class RefundCreateSerializer(serializers.Serializer):
    ticket_ids = serializers.ListField(child=serializers.UUIDField(), allow_empty=False, max_length=20)
    reason = serializers.CharField(max_length=500)
