"""Views auxiliares da PWA: service worker, manifest, offline e handler.

O service worker precisa ser servido em /sw.js (raiz) com
`Service-Worker-Allowed: /` para escopar o controle a toda a aplicação.
Por isso usamos uma view dedicada em vez de servir como static comum.

O ``DeeplinkHandlerView`` traduz URLs ``web+finanpy://...`` (registradas
no manifest via ``protocol_handlers``) para rotas internas seguras com
whitelist explícita — nunca redireciona para destinos arbitrários.
"""

from __future__ import annotations

from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

from django.conf import settings
from django.http import FileResponse, HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.views import View
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


class DeeplinkHandlerView(View):
    """Resolve URLs ``web+finanpy://...`` para rotas internas seguras.

    Registrado no ``manifest.webmanifest`` como ``protocol_handlers`` →
    ``/handler/?q=%s``. O navegador injeta a URL completa codificada no
    parâmetro ``q``.

    Whitelist de hosts/paths suportados (qualquer outro retorna 400):

    | Deeplink                                          | Redireciona para            |
    |---------------------------------------------------|-----------------------------|
    | ``web+finanpy://dashboard``                       | ``/dashboard/``             |
    | ``web+finanpy://transaction/new?<qs>``            | ``/transactions/create/?<qs>`` |
    | ``web+finanpy://transaction/<id>``                | ``/transactions/<id>/``     |
    | ``web+finanpy://budget``                          | ``/budgets/plano/``         |
    | ``web+finanpy://budget/<id>``                     | ``/budgets/plano/dashboard/<year>/<month>/`` (se possível) ou fallback |

    **Segurança:** não usa ``HttpResponseRedirect`` com URL externa em
    nenhuma hipótese. Apenas ``reverse()`` de nomes conhecidos. Querystring
    é repassada apenas para rotas que sabidamente lidam com ela
    (``/transactions/create/``).
    """

    SCHEME = 'web+finanpy'

    # Querystring keys autorizadas a passar adiante (whitelist por path)
    ALLOWED_QS = {
        'transaction_new': {
            'amount', 'description', 'category', 'category_hint',
            'transaction_type', 'account', 'transaction_date',
            'from_receipt', 'source',
        },
    }

    def get(self, request):
        raw = request.GET.get('q', '').strip()
        if not raw:
            return self._fallback('Parâmetro ?q ausente.')

        parsed = urlparse(raw)
        if parsed.scheme != self.SCHEME:
            return self._fallback('Scheme inválido.')

        host = (parsed.netloc or '').lower()
        path = (parsed.path or '').strip('/')
        qs = parse_qs(parsed.query or '', keep_blank_values=False)

        try:
            if host == 'dashboard':
                return HttpResponseRedirect(reverse('users:dashboard'))

            if host == 'transaction':
                # web+finanpy://transaction/new[?qs]
                if path == 'new' or path == '':
                    target = reverse('transactions:create')
                    safe_qs = self._filter_qs(qs, 'transaction_new')
                    if safe_qs:
                        target = f'{target}?{safe_qs}'
                    return HttpResponseRedirect(target)
                # web+finanpy://transaction/<id>
                if path.isdigit():
                    return HttpResponseRedirect(
                        reverse('transactions:detail', args=[int(path)])
                    )

            if host == 'budget':
                # web+finanpy://budget → entrada do planejamento
                # web+finanpy://budget/<plan_id> → idem (lookup de id seria
                # mais útil quando a URL de detail aceitar pk; por hora
                # caímos no entry, que lista os planos do usuário).
                return HttpResponseRedirect(reverse('budgets:planning_entry'))

        except Exception:  # noqa: BLE001
            return self._fallback('Erro ao resolver deeplink.')

        return self._fallback(f'Deeplink não suportado: {raw[:120]}')

    @classmethod
    def _filter_qs(cls, qs_dict, profile):
        allowed = cls.ALLOWED_QS.get(profile, set())
        flat = {k: v[0] for k, v in qs_dict.items() if k in allowed and v}
        return urlencode(flat)

    @staticmethod
    def _fallback(message):
        # Falha silenciosa "amigável": leva para a home com mensagem em
        # query (a home pode optar por exibir). Evita 500 no início do app
        # se o usuário tocar num link mal formatado.
        return HttpResponseRedirect(f'/?deeplink_error={message[:80]}')
