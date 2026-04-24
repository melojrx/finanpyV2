# B1 — Especificação Técnica: REST API para Agente Neo

**Objetivo**: Adicionar uma REST API ao finanpyV2 para que o sub-agente de Finanças do Neo
possa consultar e registrar dados financeiros via chamadas HTTP autenticadas por token estático.

**Estado atual do projeto**: Django 5.2 puro (MVT), sem DRF, sem rotas `/api/`.

---

## 1. Dependências

Adicionar ao `requirements.txt`:

```
djangorestframework==3.16.0
```

Não adicionar `drf-spectacular` ou `django-filter` nesta etapa — manter o escopo mínimo.

---

## 2. Alterações em `core/settings.py`

### 2.1 INSTALLED_APPS

Localizar a lista `INSTALLED_APPS` e adicionar **após** as apps Django nativas e **antes** das apps do projeto:

```python
INSTALLED_APPS = [
    # Django nativas (já existentes)
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # DRF (ADICIONAR)
    'rest_framework',
    'rest_framework.authtoken',

    # Apps do projeto (já existentes)
    'users',
    'profiles',
    'accounts',
    'categories',
    'transactions',
    'budgets',
    'goals',
]
```

### 2.2 Configuração do DRF

Adicionar ao final de `core/settings.py` (antes da seção de arquivos estáticos):

```python
# ── REST Framework ────────────────────────────────────────────────────────────
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
}
```

---

## 3. Migration para o Token

Após instalar o DRF e adicionar `rest_framework.authtoken` ao INSTALLED_APPS, executar:

```bash
python manage.py migrate
```

Isso cria a tabela `authtoken_token` no banco.

---

## 4. Criar o app `api/`

Criar a estrutura de diretórios abaixo. **Todos os arquivos são novos** — não modificar apps existentes.

```
api/
├── __init__.py          # vazio
├── serializers.py
├── views.py
├── urls.py
```

Executar para criar o app:

```bash
python manage.py startapp api
```

Remover os arquivos gerados automaticamente que não serão usados: `api/models.py`, `api/admin.py`, `api/tests.py`, `api/migrations/`. **Não adicionar `api` ao INSTALLED_APPS** — não é necessário pois não tem models próprios.

---

## 5. `api/serializers.py`

Criar o arquivo com o conteúdo exato abaixo:

```python
from decimal import Decimal
from rest_framework import serializers
from accounts.models import Account
from categories.models import Category
from transactions.models import Transaction


class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = [
            'id', 'name', 'account_type', 'balance',
            'currency', 'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'balance', 'created_at', 'updated_at']


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = [
            'id', 'name', 'category_type', 'color',
            'icon', 'parent', 'is_active',
        ]
        read_only_fields = ['id']


class TransactionSerializer(serializers.ModelSerializer):
    account_name = serializers.CharField(source='account.name', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)

    class Meta:
        model = Transaction
        fields = [
            'id',
            'transaction_type',
            'amount',
            'description',
            'transaction_date',
            'notes',
            'is_recurring',
            'recurrence_type',
            'account',
            'account_name',
            'category',
            'category_name',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'account_name', 'category_name', 'created_at', 'updated_at']

    def validate(self, data):
        user = self.context['request'].user
        account = data.get('account')
        category = data.get('category')

        if account and account.user != user:
            raise serializers.ValidationError({'account': 'Conta não pertence ao usuário.'})
        if category and category.user != user:
            raise serializers.ValidationError({'category': 'Categoria não pertence ao usuário.'})

        return data
```

---

## 6. `api/views.py`

```python
from decimal import Decimal

from django.db.models import Sum, Q
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Account
from categories.models import Category
from transactions.models import Transaction

from .serializers import AccountSerializer, CategorySerializer, TransactionSerializer


class AccountViewSet(viewsets.ReadOnlyModelViewSet):
    """Contas do usuário autenticado — somente leitura."""
    serializer_class = AccountSerializer

    def get_queryset(self):
        return Account.objects.filter(user=self.request.user).order_by('name')


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """Categorias do usuário autenticado — somente leitura."""
    serializer_class = CategorySerializer

    def get_queryset(self):
        qs = Category.objects.filter(user=self.request.user, is_active=True)
        category_type = self.request.query_params.get('type')
        if category_type in ('INCOME', 'EXPENSE'):
            qs = qs.filter(category_type=category_type)
        return qs.order_by('category_type', 'name')


class TransactionViewSet(viewsets.ModelViewSet):
    """CRUD de transações do usuário autenticado."""
    serializer_class = TransactionSerializer

    def get_queryset(self):
        qs = Transaction.objects.filter(user=self.request.user).select_related(
            'account', 'category'
        )
        params = self.request.query_params

        transaction_type = params.get('type')
        if transaction_type in ('INCOME', 'EXPENSE'):
            qs = qs.filter(transaction_type=transaction_type)

        year = params.get('year')
        month = params.get('month')
        if year:
            qs = qs.filter(transaction_date__year=int(year))
        if month:
            qs = qs.filter(transaction_date__month=int(month))

        account_id = params.get('account')
        if account_id:
            qs = qs.filter(account_id=account_id)

        category_id = params.get('category')
        if category_id:
            qs = qs.filter(category_id=category_id)

        return qs.order_by('-transaction_date', '-created_at')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class MonthlySummaryView(APIView):
    """Resumo financeiro mensal: receitas, despesas, saldo e contagem."""

    def get(self, request):
        try:
            year = int(request.query_params.get('year', 0))
            month = int(request.query_params.get('month', 0))
        except (TypeError, ValueError):
            return Response(
                {'error': 'year e month devem ser inteiros.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not (year and month):
            return Response(
                {'error': 'Parâmetros year e month são obrigatórios.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        summary = Transaction.get_monthly_summary(request.user, year, month)

        return Response({
            'year': year,
            'month': month,
            'income': str(summary['income']),
            'expenses': str(summary['expenses']),
            'balance': str(summary['balance']),
            'transaction_count': summary['transaction_count'],
        })


class YearlySummaryView(APIView):
    """Resumo financeiro anual: receitas e despesas por mês."""

    def get(self, request):
        try:
            year = int(request.query_params.get('year', 0))
        except (TypeError, ValueError):
            return Response(
                {'error': 'year deve ser inteiro.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not year:
            return Response(
                {'error': 'Parâmetro year é obrigatório.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        months = []
        for m in range(1, 13):
            s = Transaction.get_monthly_summary(request.user, year, m)
            months.append({
                'month': m,
                'income': str(s['income']),
                'expenses': str(s['expenses']),
                'balance': str(s['balance']),
                'transaction_count': s['transaction_count'],
            })

        totals = Transaction.objects.filter(
            user=request.user,
            transaction_date__year=year,
        ).aggregate(
            total_income=Sum('amount', filter=Q(transaction_type='INCOME')),
            total_expenses=Sum('amount', filter=Q(transaction_type='EXPENSE')),
        )
        total_income = totals['total_income'] or Decimal('0.00')
        total_expenses = totals['total_expenses'] or Decimal('0.00')

        return Response({
            'year': year,
            'total_income': str(total_income),
            'total_expenses': str(total_expenses),
            'total_balance': str(total_income - total_expenses),
            'months': months,
        })
```

---

## 7. `api/urls.py`

```python
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    AccountViewSet,
    CategoryViewSet,
    TransactionViewSet,
    MonthlySummaryView,
    YearlySummaryView,
)

router = DefaultRouter()
router.register(r'accounts', AccountViewSet, basename='api-account')
router.register(r'categories', CategoryViewSet, basename='api-category')
router.register(r'transactions', TransactionViewSet, basename='api-transaction')

urlpatterns = [
    path('', include(router.urls)),
    path('summary/monthly/', MonthlySummaryView.as_view(), name='api-summary-monthly'),
    path('summary/yearly/', YearlySummaryView.as_view(), name='api-summary-yearly'),
]
```

---

## 8. Registrar as rotas em `core/urls.py`

Adicionar **duas** linhas ao arquivo existente:

```python
# Adicionar import no topo (junto aos existentes)
from rest_framework.authtoken.views import obtain_auth_token

# Adicionar na lista urlpatterns (antes do bloco DEBUG)
path('api/v1/', include('api.urls')),
path('api/token/', obtain_auth_token, name='api-token'),
```

O arquivo final de `core/urls.py` deve ficar:

```python
from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.authtoken.views import obtain_auth_token

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', TemplateView.as_view(template_name='index.html'), name='home'),
    path('', include('users.urls')),
    path('profile/', include('profiles.urls')),
    path('accounts/', include('accounts.urls')),
    path('categories/', include('categories.urls')),
    path('transactions/', include('transactions.urls')),
    path('budgets/', include('budgets.urls')),

    # REST API
    path('api/v1/', include('api.urls')),
    path('api/token/', obtain_auth_token, name='api-token'),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

---

## 9. Gerar o token do agente

Após deploy (ou em desenvolvimento), executar via Django shell:

```bash
python manage.py shell -c "
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token

User = get_user_model()
# Substitua 'seu_usuario' pelo username do usuário dono dos dados
user = User.objects.get(username='seu_usuario')
token, created = Token.objects.get_or_create(user=user)
print(f'Token do agente: {token.key}')
"
```

Salvar o token gerado como variável de ambiente no VPS (`NEO_FINANPY_TOKEN`) para uso nos skills do Hermes.

---

## 10. Validação do ambiente de desenvolvimento

Após implementar tudo, verificar localmente:

```bash
# 1. Aplicar migrations
python manage.py migrate

# 2. Subir servidor
python manage.py runserver 8001

# 3. Obter token (substitua credentials reais)
curl -X POST http://localhost:8001/api/token/ \
  -H "Content-Type: application/json" \
  -d '{"username": "seu_usuario", "password": "sua_senha"}'
# Resposta esperada: {"token": "abc123..."}

# 4. Testar resumo mensal
curl http://localhost:8001/api/v1/summary/monthly/?year=2026&month=4 \
  -H "Authorization: Token abc123..."
# Resposta esperada:
# {
#   "year": 2026,
#   "month": 4,
#   "income": "0.00",
#   "expenses": "0.00",
#   "balance": "0.00",
#   "transaction_count": 0
# }

# 5. Listar contas
curl http://localhost:8001/api/v1/accounts/ \
  -H "Authorization: Token abc123..."

# 6. Listar categorias de despesa
curl "http://localhost:8001/api/v1/categories/?type=EXPENSE" \
  -H "Authorization: Token abc123..."

# 7. Criar transação
curl -X POST http://localhost:8001/api/v1/transactions/ \
  -H "Authorization: Token abc123..." \
  -H "Content-Type: application/json" \
  -d '{
    "transaction_type": "EXPENSE",
    "amount": "45.90",
    "description": "Almoço",
    "transaction_date": "2026-04-22",
    "account": 1,
    "category": 3
  }'
```

---

## 11. Referência de Endpoints

| Método | URL | Descrição |
|--------|-----|-----------|
| POST | `/api/token/` | Obtém token com username+password |
| GET | `/api/v1/accounts/` | Lista contas do usuário |
| GET | `/api/v1/accounts/{id}/` | Detalhe de uma conta |
| GET | `/api/v1/categories/` | Lista categorias (`?type=INCOME\|EXPENSE`) |
| GET | `/api/v1/categories/{id}/` | Detalhe de uma categoria |
| GET | `/api/v1/transactions/` | Lista transações (filtros abaixo) |
| POST | `/api/v1/transactions/` | Cria uma transação |
| GET | `/api/v1/transactions/{id}/` | Detalhe de uma transação |
| PATCH | `/api/v1/transactions/{id}/` | Atualiza campos de uma transação |
| DELETE | `/api/v1/transactions/{id}/` | Remove uma transação |
| GET | `/api/v1/summary/monthly/` | Resumo mensal (`?year=&month=`) |
| GET | `/api/v1/summary/yearly/` | Resumo anual por mês (`?year=`) |

### Filtros em GET /api/v1/transactions/

| Parâmetro | Valores | Exemplo |
|-----------|---------|---------|
| `type` | `INCOME` ou `EXPENSE` | `?type=EXPENSE` |
| `year` | inteiro | `?year=2026` |
| `month` | inteiro 1-12 | `?month=4` |
| `account` | ID da conta | `?account=1` |
| `category` | ID da categoria | `?category=3` |

---

## 12. Schema de request/response

### POST /api/v1/transactions/ — body obrigatório

```json
{
  "transaction_type": "EXPENSE",
  "amount": "45.90",
  "description": "Almoço restaurante",
  "transaction_date": "2026-04-22",
  "account": 1,
  "category": 3
}
```

Campos opcionais adicionais:

```json
{
  "notes": "Saída com equipe",
  "is_recurring": false,
  "recurrence_type": null
}
```

**Restrições de negócio** (já implementadas no model — o serializer as herdará via `full_clean()`):
- `transaction_date` não pode ser data futura
- `category.category_type` deve coincidir com `transaction_type` (ex.: categoria EXPENSE só em transação EXPENSE)
- `account` e `category` devem pertencer ao usuário autenticado
- `amount` deve ser positivo (> 0)
- Se `is_recurring=true`, `recurrence_type` é obrigatório

### GET /api/v1/transactions/ — response (paginado)

```json
{
  "count": 142,
  "next": "http://localhost:8001/api/v1/transactions/?page=2",
  "previous": null,
  "results": [
    {
      "id": 87,
      "transaction_type": "EXPENSE",
      "amount": "45.90",
      "description": "Almoço restaurante",
      "transaction_date": "2026-04-22",
      "notes": null,
      "is_recurring": false,
      "recurrence_type": null,
      "account": 1,
      "account_name": "Conta Corrente Itaú",
      "category": 3,
      "category_name": "Alimentação",
      "created_at": "2026-04-22T13:45:00Z",
      "updated_at": "2026-04-22T13:45:00Z"
    }
  ]
}
```

### GET /api/v1/summary/monthly/?year=2026&month=4 — response

```json
{
  "year": 2026,
  "month": 4,
  "income": "5200.00",
  "expenses": "2847.50",
  "balance": "2352.50",
  "transaction_count": 23
}
```

### GET /api/v1/summary/yearly/?year=2026 — response

```json
{
  "year": 2026,
  "total_income": "15600.00",
  "total_expenses": "9842.30",
  "total_balance": "5757.70",
  "months": [
    {"month": 1, "income": "5200.00", "expenses": "3100.00", "balance": "2100.00", "transaction_count": 18},
    {"month": 2, "income": "5200.00", "expenses": "3200.00", "balance": "2000.00", "transaction_count": 21},
    {"month": 3, "income": "5200.00", "expenses": "3542.30", "balance": "1657.70", "transaction_count": 19},
    {"month": 4, "income": "0.00", "expenses": "0.00", "balance": "0.00", "transaction_count": 0},
    ...
  ]
}
```

---

## 13. B2 — docker-compose.vps.yml

Criar `/home/jrmelo/Projetos/finanpy_v2/docker-compose.vps.yml` com o conteúdo abaixo.
Diferenças em relação ao `docker-compose.prod.yml`:
- **Sem** o serviço `nginx` (o nginx do VPS faz o proxy)
- Gunicorn exposto em `127.0.0.1:8001` apenas (não acessível externamente)
- Volume `staticfiles` montado em `/srv/finanpy/staticfiles` para o nginx do host acessar

```yaml
services:
  db:
    image: postgres:16-alpine
    restart: unless-stopped
    environment:
      POSTGRES_DB: ${POSTGRES_DB:-finanpy}
      POSTGRES_USER: ${POSTGRES_USER:-finanpy}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?set POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $${POSTGRES_USER} -d $${POSTGRES_DB}"]
      interval: 10s
      timeout: 5s
      retries: 5

  web:
    build: .
    restart: unless-stopped
    depends_on:
      db:
        condition: service_healthy
    ports:
      - "127.0.0.1:8001:8000"
    environment:
      DJANGO_SETTINGS_MODULE: core.settings_production
      SECRET_KEY: ${SECRET_KEY:?set SECRET_KEY}
      ALLOWED_HOSTS: ${ALLOWED_HOSTS:?set ALLOWED_HOSTS}
      CSRF_TRUSTED_ORIGINS: ${CSRF_TRUSTED_ORIGINS:-}
      POSTGRES_DB: ${POSTGRES_DB:-finanpy}
      POSTGRES_USER: ${POSTGRES_USER:-finanpy}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?set POSTGRES_PASSWORD}
      POSTGRES_HOST: db
      POSTGRES_PORT: 5432
      SECURE_SSL_REDIRECT: ${SECURE_SSL_REDIRECT:-true}
      SECURE_HSTS_SECONDS: ${SECURE_HSTS_SECONDS:-31536000}
      LOG_LEVEL: ${LOG_LEVEL:-INFO}
      EMAIL_BACKEND: ${EMAIL_BACKEND:-django.core.mail.backends.smtp.EmailBackend}
      EMAIL_HOST: ${EMAIL_HOST:-localhost}
      EMAIL_PORT: ${EMAIL_PORT:-587}
      EMAIL_USE_TLS: ${EMAIL_USE_TLS:-true}
      EMAIL_HOST_USER: ${EMAIL_HOST_USER:-}
      EMAIL_HOST_PASSWORD: ${EMAIL_HOST_PASSWORD:-}
      DEFAULT_FROM_EMAIL: ${DEFAULT_FROM_EMAIL:-FinanPy <noreply@finanpy.local>}
    volumes:
      - staticfiles:/app/staticfiles
      - media:/app/media
      - /srv/finanpy/staticfiles:/app/staticfiles   # bind mount para nginx do host

volumes:
  postgres_data:
  staticfiles:
  media:
```

**Nota**: o bind mount `/srv/finanpy/staticfiles` deve existir no VPS antes do deploy:
```bash
sudo mkdir -p /srv/finanpy/staticfiles /srv/finanpy/media
sudo chown -R $USER:$USER /srv/finanpy
```

---

## 14. Checklist de implementação

- [ ] Adicionar `djangorestframework==3.16.0` ao `requirements.txt`
- [ ] Adicionar `rest_framework` e `rest_framework.authtoken` ao `INSTALLED_APPS`
- [ ] Adicionar bloco `REST_FRAMEWORK` ao `core/settings.py`
- [ ] Executar `python manage.py migrate` (cria tabela de tokens)
- [ ] Criar `api/__init__.py` (vazio)
- [ ] Criar `api/serializers.py` (seção 5)
- [ ] Criar `api/views.py` (seção 6)
- [ ] Criar `api/urls.py` (seção 7)
- [ ] Atualizar `core/urls.py` (seção 8)
- [ ] Verificar com `python manage.py check` — deve retornar 0 issues
- [ ] Gerar token do agente (seção 9)
- [ ] Executar todos os curls de validação (seção 10) com respostas HTTP 200/201
- [ ] Criar `docker-compose.vps.yml` (seção 13)
- [ ] Commit e push para o GitHub

---

## 15. Notas para o agente implementador

1. **Não modificar** nenhum model, view, template ou URL existente — a API é adicionada de forma não-invasiva.
2. O método `Transaction.save()` chama `full_clean()` automaticamente — não chamar `full_clean()` manualmente no serializer `validate()`, apenas fazer as checagens de ownership de user.
3. `AccountViewSet` e `CategoryViewSet` são `ReadOnlyModelViewSet` intencionalmente — o Neo não deve criar contas ou categorias via API nesta versão.
4. A paginação retorna 50 itens por página. Para listar todas as transações de um mês use `?year=2026&month=4` — o mês geralmente tem menos de 50 transações.
5. Todos os valores monetários são retornados como `string` (Decimal serializado) para evitar perda de precisão em JSON.
6. O endpoint `/api/token/` é para uso na geração inicial do token. O Neo deve usar o token estático gerado via shell (seção 9), não autenticar dinamicamente.
