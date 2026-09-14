"""Controlled delivery of uploads stored in ``MEDIA_ROOT``."""

from django.conf import settings
from django.http import Http404
from django.views.static import serve


def serve_media(request, path):
    """Serve uploads when media delivery is enabled for this environment."""
    if not settings.DEBUG and not getattr(settings, "SERVE_MEDIA_FILES", False):
        raise Http404

    return serve(request, path, document_root=settings.MEDIA_ROOT)
