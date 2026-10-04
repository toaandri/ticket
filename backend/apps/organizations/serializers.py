from rest_framework import serializers

from .models import Organization


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = (
            "id",
            "slug",
            "name",
            "owner",
            "created_at",
        )
        read_only_fields = (
            "id",
            "owner",
            "created_at",
        )


class InvitationCreateSerializer(serializers.Serializer):
    email = serializers.EmailField()
    role = serializers.ChoiceField(choices=["MANAGER", "EDITOR", "FINANCE", "SCANNER"])


class InvitationAcceptSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=2048)


class RoleSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=["MANAGER", "EDITOR", "FINANCE", "SCANNER"])


class InvitationResultSerializer(InvitationCreateSerializer):
    id = serializers.UUIDField(read_only=True)
    expires_at = serializers.DateTimeField(read_only=True)


class MembershipResultSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    role = serializers.CharField(read_only=True)


class AcceptanceResultSerializer(serializers.Serializer):
    organization_id = serializers.UUIDField(read_only=True)
    role = serializers.CharField(read_only=True)
