from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import generics, permissions, serializers
from rest_framework.response import Response

from apps.events.models import Event
from apps.events.serializers import EventSerializer
from apps.events.services import cancel_event
from apps.notifications.models import OutboxEvent
from apps.organizations.models import Organization
from apps.organizations.serializers import OrganizationSerializer
from apps.organizations.workspace import AuditSerializer

from .models import AuditLog


class PlatformAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_superuser)


class AdminAuditView(generics.ListAPIView):
    permission_classes = (PlatformAdmin,)
    serializer_class = AuditSerializer
    queryset = AuditLog.objects.order_by("-created_at", "id")


class DeadLetterSerializer(serializers.ModelSerializer):
    class Meta:
        model = OutboxEvent
        fields = ("id", "event_type", "aggregate_id", "attempts", "failed_at", "created_at")


class DeadLetterView(generics.ListAPIView):
    permission_classes = (PlatformAdmin,)
    serializer_class = DeadLetterSerializer
    queryset = OutboxEvent.objects.filter(failed_at__isnull=False).order_by("created_at")


class ReplayOutboxView(generics.GenericAPIView):
    permission_classes = (PlatformAdmin,)
    serializer_class = DeadLetterSerializer

    @extend_schema(request=None, responses=DeadLetterSerializer)
    def post(self, request, pk):
        with transaction.atomic():
            event = get_object_or_404(
                OutboxEvent.objects.select_for_update(), pk=pk, failed_at__isnull=False, published_at__isnull=True
            )
            event.failed_at = None
            event.attempts = 0
            event.next_attempt_at = timezone.now()
            event.save(update_fields=["failed_at", "attempts", "next_attempt_at"])
            AuditLog.objects.create(
                actor=request.user, action="outbox.replayed", entity_type="OutboxEvent", entity_id=event.pk
            )
            return Response(DeadLetterSerializer(event).data)


class ModerationSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=500)
    suspended = serializers.BooleanField(default=True)


class ModerateOrganizationView(generics.GenericAPIView):
    permission_classes = (PlatformAdmin,)
    serializer_class = ModerationSerializer

    @extend_schema(responses=OrganizationSerializer)
    def post(self, request, pk):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            organization = get_object_or_404(Organization.objects.select_for_update(), pk=pk)
            organization.status = "SUSPENDED" if serializer.validated_data["suspended"] else "ACTIVE"
            organization.save(update_fields=["status"])
            AuditLog.objects.create(
                actor=request.user,
                organization=organization,
                action="organization.moderated",
                entity_type="Organization",
                entity_id=organization.pk,
                metadata_redacted={"reason": serializer.validated_data["reason"], "status": organization.status},
            )
            return Response(OrganizationSerializer(organization).data)


class ModerateEventView(generics.GenericAPIView):
    permission_classes = (PlatformAdmin,)
    serializer_class = ModerationSerializer

    @extend_schema(responses=EventSerializer)
    def post(self, request, pk):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        event = get_object_or_404(Event, pk=pk)
        event = cancel_event(
            actor=request.user, event_id=event.pk, platform_override=True, reason=serializer.validated_data["reason"]
        )
        return Response(EventSerializer(event).data)
