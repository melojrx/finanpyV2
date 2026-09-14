"""Minimal health endpoints for reverse proxies and Swarm."""

from django.db import connection
from django.db.utils import OperationalError
from django.http import JsonResponse


def liveness(request):
    """Report that the Django process can serve requests."""
    return JsonResponse({"alive": True})


def readiness(request):
    """Report readiness only when the configured database is reachable."""
    try:
        connection.ensure_connection()
    except OperationalError:
        return JsonResponse({"ready": False}, status=503)
    return JsonResponse({"ready": True})
