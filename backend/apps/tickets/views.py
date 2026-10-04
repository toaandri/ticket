from django.http import HttpResponse
from drf_spectacular.utils import OpenApiTypes, extend_schema
from rest_framework import mixins, viewsets
from rest_framework.decorators import action

from .models import Ticket
from .serializers import TicketSerializer
from .services import qr_png, ticket_pdf


class TicketViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = TicketSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Ticket.objects.none()
        return Ticket.objects.filter(holder=self.request.user).select_related(
            "event__venue", "ticket_type", "event_seat__seat", "order_item"
        )

    @extend_schema(responses={(200, "application/pdf"): OpenApiTypes.BINARY})
    @action(detail=True, methods=["get"])
    def pdf(self, request, pk=None):
        ticket = self.get_object()
        response = HttpResponse(ticket_pdf(ticket), content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{ticket.public_code}.pdf"'
        response["Cache-Control"] = "private, no-store"
        return response

    @extend_schema(responses={(200, "image/png"): OpenApiTypes.BINARY})
    @action(detail=True, methods=["get"])
    def qr(self, request, pk=None):
        response = HttpResponse(qr_png(self.get_object()), content_type="image/png")
        response["Cache-Control"] = "private, no-store"
        return response
