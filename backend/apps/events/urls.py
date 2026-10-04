from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.audit.admin_api import (
    AdminAuditView,
    DeadLetterView,
    ModerateEventView,
    ModerateOrganizationView,
    ReplayOutboxView,
)
from apps.checkins.views import CheckInView
from apps.notifications.views import NotificationViewSet
from apps.orders.views import OrderViewSet
from apps.payments.views import StripeWebhookView
from apps.promotions.views import PromotionViewSet
from apps.reservations.views import ReservationViewSet
from apps.tickets.views import TicketViewSet
from apps.venues.views import VenueViewSet

from .views import EventViewSet

router = DefaultRouter()
router.register("promotions", PromotionViewSet, basename="promotion")
router.register("notifications", NotificationViewSet, basename="notification")
router.register("events", EventViewSet, basename="event")
router.register("venues", VenueViewSet, basename="venue")
router.register("reservations", ReservationViewSet, basename="reservation")
router.register("orders", OrderViewSet, basename="order")
router.register("tickets", TicketViewSet, basename="ticket")


urlpatterns = [
    path("admin/audit/", AdminAuditView.as_view()),
    path("admin/outbox/", DeadLetterView.as_view()),
    path("admin/outbox/<uuid:pk>/replay/", ReplayOutboxView.as_view()),
    path("admin/organizations/<uuid:pk>/moderate/", ModerateOrganizationView.as_view()),
    path("admin/events/<uuid:pk>/moderate/", ModerateEventView.as_view()),
    path("check-ins/", CheckInView.as_view()),
    path("payments/stripe/webhook/", StripeWebhookView.as_view()),
    *router.urls,
]
