from typing import ClassVar

from django.db.models import Q
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import mixins, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Event
from .serializers import (
    AvailabilitySerializer,
    EventCreateSerializer,
    EventSerializer,
    TicketTypeCreateSerializer,
    TicketTypeSerializer,
)
from .services import cancel_event, configure_ticket_type, create_event, publish_event, update_event


class EventViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = EventSerializer
    permission_classes: ClassVar[list] = [permissions.IsAuthenticatedOrReadOnly]
    search_fields: ClassVar[list] = ["title", "description", "venue__city"]
    ordering_fields: ClassVar[list] = ["start_at", "created_at"]

    def get_queryset(self):
        queryset = Event.objects.select_related("venue").prefetch_related("ticket_types").order_by("start_at", "id")
        if getattr(self, "swagger_fake_view", False):
            return queryset.none()
        visible = Q(status__in=["PUBLISHED", "COMPLETED", "CANCELLED"], organization__status="ACTIVE")
        if self.request.user.is_authenticated:
            visible |= Q(organization__memberships__user=self.request.user)
        queryset = queryset.filter(visible).distinct()
        for key, lookup in [
            ("organization", "organization_id"),
            ("city", "venue__city__iexact"),
            ("category", "category__iexact"),
            ("after", "start_at__gte"),
        ]:
            value = self.request.query_params.get(key)
            if value:
                from django.core.exceptions import ValidationError as DjangoValidationError
                from rest_framework.exceptions import ValidationError

                try:
                    queryset = queryset.filter(**{lookup: value})
                except (ValueError, DjangoValidationError) as exc:
                    raise ValidationError({key: "Invalid filter."}) from exc
        return queryset

    @extend_schema(
        parameters=[OpenApiParameter(name=name, type=str) for name in ["organization", "city", "category", "after"]]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(request=EventCreateSerializer, responses={201: EventSerializer})
    def create(self, request):
        serializer = EventCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        event = create_event(actor=request.user, **serializer.validated_data)
        return Response(EventSerializer(event).data, status=201)

    @extend_schema(request=EventSerializer, responses=EventSerializer)
    def partial_update(self, request, pk=None):
        event = self.get_object()
        serializer = EventSerializer(event, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated = update_event(actor=request.user, event_id=pk, data=serializer.validated_data)
        return Response(EventSerializer(updated).data)

    @extend_schema(request=None, responses=EventSerializer)
    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def publish(self, request, pk=None):
        self.get_object()
        return Response(EventSerializer(publish_event(actor=request.user, event_id=pk)).data)

    @extend_schema(request=None, responses=EventSerializer)
    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def cancel(self, request, pk=None):
        self.get_object()
        return Response(EventSerializer(cancel_event(actor=request.user, event_id=pk)).data)

    @extend_schema(request=TicketTypeCreateSerializer, responses={201: TicketTypeSerializer})
    @action(detail=True, methods=["post"], url_path="ticket-types", permission_classes=[permissions.IsAuthenticated])
    def ticket_types(self, request, pk=None):
        self.get_object()
        serializer = TicketTypeCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ticket_type = configure_ticket_type(actor=request.user, event_id=pk, **serializer.validated_data)
        return Response(TicketTypeSerializer(ticket_type).data, status=201)

    @extend_schema(responses=AvailabilitySerializer)
    @action(detail=True, methods=["get"])
    def availability(self, request, pk=None):
        event = self.get_object()
        buckets = [
            {
                "ticket_type_id": bucket.ticket_type_id,
                "capacity": bucket.capacity,
                "held": bucket.held_count,
                "sold": bucket.sold_count,
                "available": bucket.capacity - bucket.held_count - bucket.sold_count,
            }
            for bucket in event.inventory.all()
        ]
        seats = event.seats.select_related("seat", "claim").order_by("seat__row_label", "seat__seat_number")
        return Response(
            AvailabilitySerializer(
                {"event_id": event.pk, "version": event.version, "ticket_types": buckets, "seats": seats}
            ).data
        )
