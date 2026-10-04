from django.conf import settings
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from apps.common.domain import idempotency_key, require_role
from apps.payments.models import PaymentAttempt
from apps.payments.services import initiate_payment, process_payment_event, refund_order

from .models import Order
from .serializers import (
    OrderCreateSerializer,
    OrderSerializer,
    PaymentCreateSerializer,
    PaymentSerializer,
    RefundCreateSerializer,
    RefundSerializer,
    SimulationSerializer,
)
from .services import create_order

IDEMPOTENCY = [OpenApiParameter("Idempotency-Key", str, OpenApiParameter.HEADER, required=True)]


class OrderViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = OrderSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Order.objects.none()
        if self.action == "refunds":
            return Order.objects.filter(event__organization__memberships__user=self.request.user)
        return (
            Order.objects.filter(user=self.request.user)
            .select_related("event")
            .prefetch_related("items", "payments", "refunds")
        )

    @extend_schema(request=OrderCreateSerializer, responses={201: OrderSerializer}, parameters=IDEMPOTENCY)
    def create(self, request):
        serializer = OrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = create_order(actor=request.user, key=idempotency_key(request), **serializer.validated_data)
        return Response(OrderSerializer(order).data, status=201)

    @extend_schema(request=PaymentCreateSerializer, responses={201: PaymentSerializer}, parameters=IDEMPOTENCY)
    @action(detail=True, methods=["post"])
    def payments(self, request, pk=None):
        self.get_object()
        serializer = PaymentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payment = initiate_payment(
            actor=request.user, order_id=pk, key=idempotency_key(request), **serializer.validated_data
        )
        return Response(PaymentSerializer(payment).data, status=201)

    @extend_schema(request=SimulationSerializer, responses=PaymentSerializer, parameters=IDEMPOTENCY)
    @action(detail=True, methods=["post"], url_path="simulate-payment")
    def simulate_payment(self, request, pk=None):
        self.get_object()
        if not settings.DEBUG:
            raise PermissionDenied("Payment simulation is disabled outside development.")
        serializer = SimulationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payment = get_object_or_404(
            PaymentAttempt, pk=serializer.validated_data["payment_id"], order_id=pk, provider="MOCK"
        )
        payment = process_payment_event(
            payment_id=payment.pk,
            provider_event_id=f"simulation:{request.user.pk}:{idempotency_key(request)}",
            status=serializer.validated_data["outcome"],
            amount=payment.amount_minor,
            currency=payment.currency,
        )
        return Response(PaymentSerializer(payment).data)

    @extend_schema(request=RefundCreateSerializer, responses={201: RefundSerializer}, parameters=IDEMPOTENCY)
    @action(detail=True, methods=["post"])
    def refunds(self, request, pk=None):
        order = self.get_object()
        require_role(request.user, order.event.organization_id, ("OWNER", "MANAGER"))
        serializer = RefundCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        refund = refund_order(
            actor=request.user, order_id=pk, key=idempotency_key(request), **serializer.validated_data
        )
        return Response(RefundSerializer(refund).data, status=201)
