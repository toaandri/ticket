"""ASGI config for Ticket platform (HTTP + WebSocket via Django Channels)."""

import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

django_asgi_app = get_asgi_application()

# WebSocket URL patterns will be registered as apps are implemented
from django.urls import path  # noqa: E402

from apps.events.consumers import AvailabilityConsumer  # noqa: E402

websocket_urlpatterns = (path("ws/events/<uuid:event_id>/availability/", AvailabilityConsumer.as_asgi()),)

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AllowedHostsOriginValidator(AuthMiddlewareStack(URLRouter(websocket_urlpatterns))),
    }
)
