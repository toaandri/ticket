from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.checkins.views import CheckInView
from apps.orders.views import OrderViewSet
from apps.payments.views import StripeWebhookView
from apps.reservations.views import ReservationViewSet
from apps.tickets.views import TicketViewSet
from apps.venues.views import VenueViewSet

from .views import EventViewSet

router = DefaultRouter()
router.register("events", EventViewSet, basename="event")
router.register("venues", VenueViewSet, basename="venue")
router.register("reservations", ReservationViewSet, basename="reservation")
router.register("orders", OrderViewSet, basename="order")
router.register("tickets", TicketViewSet, basename="ticket")
urlpatterns = [
    path("check-ins/", CheckInView.as_view()),
    path("payments/stripe/webhook/", StripeWebhookView.as_view()),
    *router.urls,
]
