from django.db import IntegrityError, transaction
from rest_framework import generics
from rest_framework.exceptions import ValidationError

from .models import Organization
from .serializers import OrganizationSerializer
from .services import create_organization


class OrganizationListView(generics.ListCreateAPIView):
    serializer_class = OrganizationSerializer

    def get_queryset(self):
        return Organization.objects.filter(memberships__user=self.request.user).order_by("created_at", "id")

    def perform_create(self, serializer):
        try:
            with transaction.atomic():
                serializer.instance = create_organization(owner=self.request.user, **serializer.validated_data)
        except IntegrityError as exc:
            raise ValidationError({"slug": "This organization slug is already taken."}) from exc


class OrganizationDetailView(generics.RetrieveAPIView):
    serializer_class = OrganizationSerializer

    def get_queryset(self):
        # Scope before lookup: guessed UUIDs do not reveal another organization's existence.
        return Organization.objects.filter(memberships__user=self.request.user)
