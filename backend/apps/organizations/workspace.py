from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiTypes, extend_schema
from rest_framework import generics, serializers
from rest_framework.response import Response

from apps.analytics.serializers import EventMetricsSerializer
from apps.analytics.services import event_metrics, orders_csv
from apps.audit.models import AuditLog
from apps.common.domain import require_role
from apps.events.models import Event
from apps.orders.models import Order
from apps.orders.serializers import OrderSerializer

from .models import EventStaffAssignment, Membership, Organization


class MemberSerializer(serializers.ModelSerializer):
    email = serializers.CharField(source="user.email", read_only=True)
    display_name = serializers.CharField(source="user.display_name", read_only=True)

    class Meta:
        model = Membership
        fields = ("id", "email", "display_name", "role", "joined_at")


class AuditSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = ("id", "action", "entity_type", "entity_id", "metadata_redacted", "created_at")


class MembersView(generics.ListAPIView):
    serializer_class = MemberSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Membership.objects.none()
        organization = get_object_or_404(Organization, pk=self.kwargs["pk"], memberships__user=self.request.user)
        require_role(self.request.user, organization.pk, ("OWNER", "MANAGER", "EDITOR", "FINANCE"))
        return Membership.objects.filter(organization=organization).select_related("user").order_by("joined_at")


class OrganizationAuditView(generics.ListAPIView):
    serializer_class = AuditSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return AuditLog.objects.none()
        organization = get_object_or_404(Organization, pk=self.kwargs["pk"], memberships__user=self.request.user)
        require_role(self.request.user, organization.pk, ("OWNER", "MANAGER"))
        return AuditLog.objects.filter(organization=organization).order_by("-created_at", "id")


class OrganizationOrdersView(generics.ListAPIView):
    serializer_class = OrderSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Order.objects.none()
        organization = get_object_or_404(Organization, pk=self.kwargs["pk"], memberships__user=self.request.user)
        require_role(self.request.user, organization.pk, ("OWNER", "MANAGER", "FINANCE"))
        return (
            Order.objects.filter(event__organization=organization)
            .select_related("event")
            .prefetch_related("items", "payments", "refunds")
        )


class EventMetricsView(generics.GenericAPIView):
    serializer_class = EventMetricsSerializer

    @extend_schema(responses=EventMetricsSerializer)
    def get(self, request, pk):
        event = get_object_or_404(Event, pk=pk, organization__memberships__user=request.user)
        return Response(event_metrics(actor=request.user, event=event))


class EventExportView(generics.GenericAPIView):
    serializer_class = EventMetricsSerializer

    @extend_schema(responses={(200, "text/csv"): OpenApiTypes.STR})
    def get(self, request, pk):
        event = get_object_or_404(Event, pk=pk, organization__memberships__user=request.user)
        response = HttpResponse(orders_csv(actor=request.user, event=event), content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="orders.csv"'
        response["Cache-Control"] = "private, no-store"
        return response


class AssignmentCreateSerializer(serializers.Serializer):
    membership_id = serializers.UUIDField()


class AssignmentSerializer(serializers.ModelSerializer):
    membership_id = serializers.UUIDField()

    class Meta:
        model = EventStaffAssignment
        fields = ("id", "membership_id")


class EventStaffView(generics.GenericAPIView):
    serializer_class = AssignmentCreateSerializer

    @extend_schema(responses={201: AssignmentSerializer})
    def post(self, request, pk):
        from django.db import transaction

        with transaction.atomic():
            event = get_object_or_404(Event.objects.select_for_update(), pk=pk)
            require_role(request.user, event.organization_id, ("OWNER", "MANAGER"))
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            member = get_object_or_404(
                Membership,
                pk=serializer.validated_data["membership_id"],
                organization_id=event.organization_id,
                role__in=["OWNER", "MANAGER", "SCANNER"],
            )
            assignment, _created = EventStaffAssignment.objects.get_or_create(event=event, membership=member)
            AuditLog.objects.create(
                actor=request.user,
                organization_id=event.organization_id,
                event=event,
                action="staff.assigned",
                entity_type="EventStaffAssignment",
                entity_id=assignment.pk,
            )
            return Response(AssignmentSerializer(assignment).data, status=201)


class StaffEventsView(generics.ListAPIView):
    from apps.events.serializers import EventSerializer

    serializer_class = EventSerializer

    def get_queryset(self):
        from django.db.models import Q

        if getattr(self, "swagger_fake_view", False):
            return Event.objects.none()
        return (
            Event.objects.filter(
                Q(
                    organization__memberships__user=self.request.user,
                    organization__memberships__role__in=["OWNER", "MANAGER"],
                )
                | Q(
                    staff_assignments__membership__user=self.request.user,
                    staff_assignments__membership__role="SCANNER",
                )
            )
            .filter(status="PUBLISHED")
            .distinct()
            .order_by("start_at", "id")
        )


class TicketReportSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    status = serializers.CharField()
    public_code = serializers.CharField()
    ticket_type_name = serializers.CharField(source="ticket_type.name")
    seat_label = serializers.CharField(source="event_seat.seat.label", default=None, allow_null=True)
    admission_price_minor = serializers.IntegerField()
    order_id = serializers.UUIDField(source="order_item.order_id")


class OrganizationTicketsView(generics.ListAPIView):
    serializer_class = TicketReportSerializer

    def get_queryset(self):
        from apps.tickets.models import Ticket

        if getattr(self, "swagger_fake_view", False):
            return Ticket.objects.none()
        organization = get_object_or_404(Organization, pk=self.kwargs["pk"], memberships__user=self.request.user)
        require_role(self.request.user, organization.pk, ("OWNER", "MANAGER", "FINANCE"))
        queryset = Ticket.objects.filter(event__organization=organization).select_related(
            "ticket_type", "event_seat__seat", "order_item"
        )
        if self.request.query_params.get("order"):
            order = get_object_or_404(Order, pk=self.request.query_params["order"], event__organization=organization)
            queryset = queryset.filter(order_item__order=order)
        return queryset
