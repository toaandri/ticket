from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import mixins, viewsets
from rest_framework.exceptions import ValidationError

from apps.common.domain import Conflict, require_role
from apps.events.models import Event
from apps.organizations.models import Organization

from .models import Promotion
from .serializers import PromotionSerializer


class PromotionViewSet(
    mixins.ListModelMixin, mixins.CreateModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet
):
    serializer_class = PromotionSerializer
    http_method_names = ("get", "post", "patch", "head", "options")

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Promotion.objects.none()
        return Promotion.objects.filter(
            organization__memberships__user=self.request.user,
            organization__memberships__role__in=["OWNER", "MANAGER", "EDITOR"],
        ).order_by("-created_at", "id")

    @transaction.atomic
    def perform_create(self, serializer):
        data = serializer.validated_data
        org = get_object_or_404(Organization.objects.select_for_update(), pk=data["organization_id"])
        require_role(self.request.user, org.pk)
        if data.get("event_id") and not Event.objects.filter(pk=data["event_id"], organization=org).exists():
            raise ValidationError("Promotion event must belong to the organization.")
        if Promotion.objects.filter(organization=org, code=data["code"]).exists():
            raise Conflict("Promotion code already exists.")
        serializer.save()

    @transaction.atomic
    def perform_update(self, serializer):
        promotion = Promotion.objects.select_for_update().get(pk=serializer.instance.pk)
        require_role(self.request.user, promotion.organization_id)
        data = serializer.validated_data
        if any(key in data for key in ["organization_id", "event_id", "kind", "amount", "code", "currency"]):
            raise Conflict("Pricing and scope are immutable; create a new promotion or disable this one.")
        serializer.save()
