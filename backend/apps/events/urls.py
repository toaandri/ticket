from rest_framework.routers import DefaultRouter

from apps.reservations.views import ReservationViewSet
from apps.venues.views import VenueViewSet

from .views import EventViewSet

router = DefaultRouter()
router.register("events", EventViewSet, basename="event")
router.register("venues", VenueViewSet, basename="venue")
router.register("reservations", ReservationViewSet, basename="reservation")
urlpatterns = router.urls
