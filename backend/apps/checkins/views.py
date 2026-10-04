from drf_spectacular.utils import extend_schema
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from apps.common.domain import idempotency_key
from apps.orders.views import IDEMPOTENCY

from .serializers import CheckInCreateSerializer, CheckInSerializer
from .services import check_in


class CheckInView(generics.GenericAPIView):
    serializer_class = CheckInCreateSerializer
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = "checkin"

    @extend_schema(responses={201: CheckInSerializer, 409: CheckInSerializer}, parameters=IDEMPOTENCY)
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        scan = check_in(actor=request.user, key=idempotency_key(request), **serializer.validated_data)
        return Response(CheckInSerializer(scan).data, status=201 if scan.result == "ACCEPTED" else 409)
