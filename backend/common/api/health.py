"""Liveness and readiness endpoints.

Kept outside DRF (plain Django views) so they have no dependency on
authentication, permissions, or the API versioning scheme, and stay usable
by infrastructure health checks that don't send credentials.
"""

from django.db import connections
from django.db.utils import OperationalError
from django.http import JsonResponse


def liveness(request):
    return JsonResponse({"status": "ok"})


def readiness(request):
    try:
        connections["default"].ensure_connection()
    except OperationalError:
        return JsonResponse({"status": "unavailable", "database": "down"}, status=503)
    return JsonResponse({"status": "ok", "database": "up"})
