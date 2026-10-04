from rest_framework import serializers

from .models import Promotion


class PromotionSerializer(serializers.ModelSerializer):
    organization_id = serializers.UUIDField()
    event_id = serializers.UUIDField(required=False, allow_null=True)
    currency = serializers.ChoiceField(choices=["EUR", "USD", "MGA"], default="EUR")

    class Meta:
        model = Promotion
        fields = (
            "id",
            "organization_id",
            "event_id",
            "code",
            "kind",
            "amount",
            "currency",
            "usage_limit",
            "per_user_limit",
            "start_at",
            "end_at",
            "active",
        )
        read_only_fields = ("id",)

    def validate(self, data):
        instance = self.instance

        def value(field):
            return data.get(field, getattr(instance, field, None))

        if value("start_at") >= value("end_at"):
            raise serializers.ValidationError("Promotion start must precede end.")
        if value("kind") == "PERCENT" and value("amount") > 100:
            raise serializers.ValidationError("A percentage cannot exceed 100.")
        if data.get("usage_limit", 1) < 1 or data.get("per_user_limit", 1) < 1:
            raise serializers.ValidationError("Usage limits must be positive.")
        if "code" in data:
            data["code"] = data["code"].strip().upper()
        return data
