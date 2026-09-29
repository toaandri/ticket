"""Health check endpoint — returns 200 if the service is up."""

from django.http import JsonResponse
from django.views import View


class HealthCheckView(View):
    """Simple liveness probe — no DB query, just a 200."""

    def get(self, request):
        return JsonResponse({"status": "ok", "service": "ticket-backend"})
