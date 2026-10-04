from drf_spectacular.utils import extend_schema
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Venue
from .serializers import (
    SeatsCreateSerializer,
    SeatSerializer,
    SectionSerializer,
    VenueCreateSerializer,
    VenueSerializer,
)
from .services import add_seats, add_section, create_venue, update_venue


class VenueViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = VenueSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Venue.objects.none()
        return (
            Venue.objects.filter(organization__memberships__user=self.request.user)
            .prefetch_related("sections__seats")
            .order_by("name", "id")
        )

    @extend_schema(request=VenueCreateSerializer, responses={201: VenueSerializer})
    def create(self, request):
        serializer = VenueCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        venue = create_venue(actor=request.user, **serializer.validated_data)
        return Response(VenueSerializer(venue).data, status=201)

    @extend_schema(request=VenueSerializer, responses=VenueSerializer)
    def partial_update(self, request, pk=None):
        venue = self.get_object()
        serializer = VenueSerializer(venue, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated = update_venue(actor=request.user, venue_id=pk, data=serializer.validated_data)
        return Response(VenueSerializer(updated).data)

    @extend_schema(request=SectionSerializer, responses={201: SectionSerializer})
    @action(detail=True, methods=["post"])
    def sections(self, request, pk=None):
        self.get_object()
        serializer = SectionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        section = add_section(actor=request.user, venue_id=pk, **serializer.validated_data)
        return Response(SectionSerializer(section).data, status=201)

    @extend_schema(request=SeatsCreateSerializer, responses={201: SeatSerializer(many=True)})
    @action(detail=True, methods=["post"])
    def seats(self, request, pk=None):
        self.get_object()
        serializer = SeatsCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        seats = add_seats(actor=request.user, venue_id=pk, **serializer.validated_data)
        return Response(SeatSerializer(seats, many=True).data, status=201)
