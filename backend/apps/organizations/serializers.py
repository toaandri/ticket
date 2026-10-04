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
