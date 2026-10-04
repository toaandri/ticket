from typing import ClassVar

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from apps.common.domain import idempotency_key

from .models import Reservation
from .serializers import HoldCreateSerializer, ReservationSerializer
from .services import cancel_hold, create_hold


class ReservationViewSet(mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = ReservationSerializer
    throttle_classes: ClassVar[list] = [ScopedRateThrottle]
    throttle_scope = "hold"

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Reservation.objects.none()
        return Reservation.objects.filter(user=self.request.user).prefetch_related("items__ticket_type")

    @extend_schema(
        request=HoldCreateSerializer,
        responses={201: ReservationSerializer},
        parameters=[OpenApiParameter("Idempotency-Key", str, OpenApiParameter.HEADER, required=True)],
    )
    def create(self, request):
        serializer = HoldCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        hold = create_hold(actor=request.user, key=idempotency_key(request), **serializer.validated_data)
        return Response(ReservationSerializer(hold).data, status=201)

    @extend_schema(request=None, responses=ReservationSerializer)
    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        self.get_object()
        return Response(ReservationSerializer(cancel_hold(actor=request.user, reservation_id=pk)).data)
