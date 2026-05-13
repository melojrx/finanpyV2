"""Views auxiliares da PWA: service worker, manifest e página offline.

O service worker precisa ser servido em /sw.js (raiz) com
`Service-Worker-Allowed: /` para escopar o controle a toda a aplicação.
Por isso usamos uma view dedicada em vez de servir como static comum.
"""

from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.http import FileResponse, HttpResponse
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_GET
from django.views.generic import TemplateView

STATIC_ROOT = Path(settings.BASE_DIR) / "static"


@require_GET
@cache_control(no_cache=True, max_age=0)
def service_worker(request):
    """Serve /sw.js com escopo raiz e sem cache de browser (controle do SW = Workbox)."""
    sw_path = STATIC_ROOT / "sw.js"
    response = FileResponse(open(sw_path, "rb"), content_type="application/javascript")
    response["Service-Worker-Allowed"] = "/"
    response["Cache-Control"] = "no-cache, max-age=0"
    return response


@require_GET
def manifest(request):
    """Serve o manifest na raiz com Content-Type correto."""
    manifest_path = STATIC_ROOT / "manifest.webmanifest"
    response = FileResponse(open(manifest_path, "rb"), content_type="application/manifest+json")
    response["Cache-Control"] = "public, max-age=3600"
    return response


class OfflineView(TemplateView):
    """Página de fallback servida pelo SW quando a rede falha."""
    template_name = "offline.html"
