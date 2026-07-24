# MCP FinanPy v1.1 — Especificação de Design

> Status: Aprovado (brainstorming)
> Criado: 2026-07-24
> Substitui: `2026-06-06-mcp-finanpy-design.md` (v0 direct-DB, defasada)
> Autor: Junior Melo + Neo

## 1. Visão Geral

**O que é:** MCP Server (Model Context Protocol) que expõe tools do FinanPy
ao agente Hermes na VPS via JSON-RPC over stdio, consumindo a API REST do
FinanPy (DRF) em loopback.

**Por que refazer:** A implementação atual em `mcp/finanpy_mcp/` acessa o
banco diretamente (SQLite/PostgreSQL), bypassando Django ORM, signals de
saldo, serializers, validação, e os endpoints da Sprint 8 PWA. Tem bug de
SQL placeholder (`client.py:195` usa `?` para Postgres), não valida
`FINANFY_TOKEN`, e reimplementa update de saldo manualmente — duplicação
perigosa que pode divergir do signal real. Tools de budgets, goals e
plans são stubs TODO.

**Padrão de referência:** `/opt/brabus-mcp/` — FastMCP + httpx + Bearer
Token + sanitização de segredos/PII + contrato uniforme
`{ok, endpoint, params, payload}`.

**Fluxo de uma chamada do Hermes:**

```
Hermes (Neo) ──stdio──> finanpy-mcp (FastMCP)
                          │
                          │ httpx + Bearer DRF Token
                          ▼
                        Django REST Framework (/api/v1/)
                          │
                          ▼
                        Django ORM + signals + serializers + Sprint 8
                          │
                          ▼
                        Resposta JSON
                          │
                          ▼
                        Sanitização (regex de segredos)
                          │
                          ▼
                        JSON para Hermes
```

## 2. Decisões (brainstorming)

| # | Questão | Decisão |
|---|---|---|
| 1 | Acesso do MCP ao backend | Via HTTP API + DRF Token (padrão brabus) |
| 2 | Perfil Hermes com acesso | Só Neo principal; `agente-braba` fica isolado |
| 3 | Identidade do agente | Usuário Django dedicado `hermes` com DRF Token via CLI |
| 4 | Escopo v1 | Médio: leitura + criar transação + contribution + categorias/tags |
| 5 | Segredo | Env var no `config.yaml` do Hermes (sem KeePass) |
| 6 | Substituição do MCP atual | Refatorar in-place; git tag `mcp/v0-direct-db` antes do rewrite |
| 7 | Deploy | Script local + rsync manual (sem CI por enquanto) |
| 8 | Gestão de token | Mínimo: `drf_create_token` via CLI (sem UX administrativa v1) |
| 9 | Categorias/tags via MCP | Criar/editar — não expor delete (CASCADE destrói transações) |

## 3. Arquitetura

### 3.1 Componentes

- **FastMCP** como runtime MCP (mesma família do `brabus-mcp`).
- **httpx.Client** como cliente HTTP com Bearer, timeout 20s,
  `follow_redirects=False`.
- **sanitization.py** redando chaves `token|secret|password|authorization|
  api_key|bearer|cookie|session` em qualquer payload (recursivo).
- **config.py** carrega `FINANPY_API_BASE_URL` e `FINANPY_API_TOKEN` do env.
- **12 + 6 tools MCP** distribuídas por domínio em `tools/`.

### 3.2 Estrutura de diretórios

```
mcp/
├── finanpy_mcp/
│   ├── __init__.py
│   ├── server.py              # FastMCP instance + registro de tools
│   ├── config.py              # Carrega FINANPY_API_BASE_URL, FINANPY_API_TOKEN
│   ├── http_client.py         # Wrapper httpx: Bearer, timeout, sanitização
│   ├── sanitization.py        # Regex de segredos + máscara recursiva
│   ├── smoke.py               # Script de smoke pós-deploy
│   └── tools/
│       ├── __init__.py
│       ├── health.py
│       ├── accounts.py
│       ├── categories.py
│       ├── tags.py
│       ├── transactions.py
│       ├── reports.py
│       ├── budgets.py
│       ├── goals.py
│       └── plans.py
├── pyproject.toml             # mcp[cli]>=1.0, httpx, python-dotenv, dev: pytest+respx
├── run_mcp.py                 # asyncio.run(server.main())
├── .env.example
├── HERMES_CONFIG.md           # Snippet config.yaml
├── scripts/
│   ├── deploy_vps.sh          # rsync + install + restart + smoke
│   └── setup_hermes_user.sh   # Cria user Django + DRF Token
└── tests/
    ├── test_http_client.py    # httpx.MockTransport: 200/400/401/500/timeout
    ├── test_sanitization.py   # dicionários aninhados redados
    └── test_tools_contract.py # respx: cada tool, payload normalizado
```

### 3.3 Backend — FinanPy

- Django 5.2+ container `finanpy-web-1` escutando em `127.0.0.1:8001` na
  VPS (`docker-compose.vps.yml`).
- DRF com `TokenAuthentication` global (settings.py:153).
- Endpoints já implementados para PWA/Background Sync em `api/urls.py`:
  `transactions/quick/`, `dashboard/snapshot/`, `sync/since/`,
  `summary/monthly`, `summary/yearly`, `transactions/from-receipt/`.
- **Patch necessário (no mesmo PR do MCP):** `MonthlyPlanViewSet.get_queryset`
  não filtra por `year`/`month` query params. Adicionar 8 linhas para
  habilitarfiltragem e o MCP fazer 1 chamada só.

## 4. Tools MCP v1.1 (18 tools)

Contrato uniforme: `{ok: bool, endpoint: str, params: dict, payload: dict|list}`
em sucesso; `{ok: false, error: str, code?: str}` em erro.

### 4.1 Health

| # | Tool | Method + Path | Notas |
|---|---|---|---|
| 1 | `health()` | `GET /accounts/` | Verifica URL+token 200 |

### 4.2 Visão / Relatórios

| # | Tool | Method + Path | Notas |
|---|---|---|---|
| 2 | `dashboard_snapshot(include=None)` | `GET /dashboard/snapshot/?include=` | CSV: `budgets,goals,chart_6m`. Default: vazio |
| 3 | `monthly_summary(year, month)` | `GET /summary/monthly/?year=&month=` | |
| 4 | `yearly_summary(year)` | `GET /summary/yearly/?year=` | |

### 4.3 Accounts / Categories / Tags

| # | Tool | Method + Path | Notas |
|---|---|---|---|
| 5 | `list_accounts()` | `GET /accounts/` | |
| 6 | `list_categories(category_type=None)` | `GET /categories/?type=INCOME/EXPENSE` | |
| 7 | `list_subcategories(parent_id=None)` | `GET /categories/` + filtro pós-fetch | Sem `parent_id`: árvore completa; com: só filhas diretas |
| 8 | `create_category(name, category_type, color="#10B981", icon="💰", parent=None, is_active=True)` | `POST /categories/` | Validação client-side `category_type ∈ {"INCOME","EXPENSE"}`; `color` regex `^#[0-9A-Fa-f]{6}$`; `name` truncado 50 chars |
| 9 | `update_category(id, name=None, category_type=None, color=None, icon=None, parent=None, is_active=None)` | `PATCH /categories/{id}/` | Desativar via `is_active=False` |
| 10 | `list_tags()` | `GET /tags/` | |
| 11 | `create_tag(name)` | `POST /tags/` | Normaliza lower/strip (backend unique constraint) |
| 12 | `update_tag(id, name)` | `PATCH /tags/{id}/` | |

> **Sem `delete_category` / `delete_tag` no MCP**: `Transaction.category`
> é `on_delete=CASCADE` (transactions/models.py:78) e `Category.parent` é
> `on_delete=CASCADE` (categories/models.py:124). Hard-delete por agente
> LLM = risco de data loss irreversível. `Tag` é M2M → safe, mas excluído
> por coerência com o pedido (só create/edit).

### 4.4 Transactions

| # | Tool | Method + Path | Notas |
|---|---|---|---|
| 13 | `list_transactions(year=None, month=None, account=None, transaction_type=None, category=None, status=None, page=1, page_size=50)` | `GET /transactions/` | DRF pagination nativa |
| 14 | `register_quick_transaction(amount, transaction_type, account, category, description=None, transaction_date=None, notes=None, client_id=None)` | `POST /transactions/quick/` | Gera `client_id` uuid4 se ausente — idempotência 24h nativa do backend |
| 15 | `confirm_pending_transaction(id)` | `POST /transactions/{id}/confirm/` | Apenas status=PENDING |

### 4.5 Budgets / Goals / Plans

| # | Tool | Method + Path | Notas |
|---|---|---|---|
| 16 | `list_budgets(year=None, month=None, active=None)` | `GET /budgets/` | |
| 17 | `list_goals(status=None)` | `GET /goals/` | `?status=ACTIVE/COMPLETED/CANCELLED` |
| 18 | `get_monthly_plan(year, month)` | `GET /monthly-plans/?year=&month=` | Depende do patch em §3.3 |

### 4.6 Goals — contribuições

| # | Tool | Method + Path | Notas |
|---|---|---|---|
| 19 | `add_goal_contribution(goal_id, amount, date=None)` | `POST /goal-contributions/` | `date` default hoje |

> Originalmente numerados como 18 tools; a expansão de categorias/tags
> elevou o total para 19. Numeração lúcida acima.

## 5. Configuração

### 5.1 Variáveis de ambiente (`.env.example`)

```bash
# FinanPy Backend
FINANPY_API_BASE_URL=http://127.0.0.1:8001/api/v1/
FINANPY_API_TOKEN=<cole-aqui-o-token-do-user-hermes>
```

### 5.2 Regex de validação no startup

- `FINANPY_API_BASE_URL`: obrigatoriamente termina com `/api/v1/` —
  `ValueError` no startup caso contrário (fail-secure).
- `FINANPY_API_TOKEN`: mínimo 20 chars
  (`_token_looks_usable`, espelho brabus).

### 5.3 Snippet do config.yaml do Hermes

```yaml
mcp_servers:
  finanpy:
    command: /opt/finanpy-mcp/.venv/bin/python
    args: [/opt/finanpy-mcp/run_mcp.py]
    timeout: 60
    connect_timeout: 30
    env:
      FINANPY_API_BASE_URL: http://127.0.0.1:8001/api/v1/
      FINANPY_API_TOKEN: <cole-aqui-token-do-user-hermes>
    enabled: true

# Perfil agente-braba: NÃO herdamcp_servers globais (policy via
# `mcp_exclude` ou equivalente no profile) — finanpy exclusivo do Neo.
```

### 5.4 Setup único do user `hermes`

Dentro do container `finanpy-web-1` na VPS:

```bash
docker exec -it finanpy-web-1 python manage.py shell <<'PY'
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
U = get_user_model()
u, created = U.objects.get_or_create(
    username='hermes',
    defaults={'email': 'hermes@finanpy.local', 'is_active': True}
)
t, _ = Token.objects.get_or_create(user=u)
print(t.key)
PY
```

Copiar a chave para `FINANPY_API_TOKEN` no `config.yaml` do Hermes. Para
rotacionar: deletar token via admin Django e recriar — documentar em
`HERMES_CONFIG.md`.

## 6. Segurança

| Camada | Medida |
|---|---|
| Rede | Comunicação MCP↔Django em `127.0.0.1` (loopback, sem TLS) |
| Auth | Bearer DRF Token por request (`Authorization: Token <key>`) |
| Token | Env var no `config.yaml` do Hermes; owner `hermes-admin` mode 600 |
| Sanitização | Regex recursivo em `payload`, `params` e `params` aninhado: `token\|secret\|password\|authorization\|api_key\|bearer\|cookie\|session` (case-insensitive) → `"***redacted***"` |
| Redirecionamento | `follow_redirects=False` (corta redirect a outro host) |
| Whitelist | `register_quick_transaction` só envia campos authoritative; outros args não passam para a API |
| Fail-secure | `FINANPY_API_BASE_URL` sem `/api/v1/` no final → ValueError no startup |
| Logs | `logging.getLogger("httpx").setLevel(WARNING)` |
| Isolamento Hermes | Só Neo principal habilita finanpy; agente-braba via `mcp_exclude` |
| Destrutivos | Sem `delete_category`/`delete_tag`/`delete_transaction`/`delete_goal` no MCP (proteção contra data loss irreversível) |

## 7. Tratamento de erros

| Situação | Resposta do MCP |
|---|---|
| Timeout httpx | `{ok:false, error:"Tempo esgotado ao consultar a API do FinanPy."}` |
| ConnectionError httpx | `{ok:false, error:"Falha de comunicação ao consultar a API do FinanPy."}` |
| HTTP 401 | `{ok:false, error:"Token FinanPy inválido ou expirado."}` |
| HTTP 400 (DRF detail) | `{ok:false, error:"FinanPy rejeitou a operação: <detail sanitizado>"}` |
| HTTP 404 | `{ok:false, error:"Recurso FinanPy não encontrado."}` |
| HTTP ≥ 500 | `{ok:false, error:"FinanPy API erro HTTP <status>."}` — sem traceback |
| Response não-JSON | `{ok:false, error:"Resposta não-JSON recebida da API do FinanPy."}` |

Todos os erros viram dicionários no formato `{ok:false, error:str}` —
nunca exception estourada em direção ao Hermes, que ficaria truncado
no stdout do gateway.

## 8. Sanitização

`mcp/finanpy_mcp/sanitization.py` — espelho do brabus sem a parte de
PII de cliente (FinanPy não tem CPF/CNPJ/telefone de cliente).

```python
_SECRET_KEY_RE = re.compile(
    r"(token|secret|password|authorization|api[_-]?key|bearer|cookie|session)",
    re.I
)

def _mask_value(key, value):
    if value is None:
        return None
    if _SECRET_KEY_RE.search(key):
        return "***redacted***"
    return value

def _sanitize_payload(value, *, key=""):
    masked = _mask_value(key, value) if key else value
    if masked != value:
        return masked
    if isinstance(value, dict):
        return {str(k): _sanitize_payload(v, key=str(k)) for k, v in value.items()}
    if isinstance(value, list):
        return [_sanitize_payload(item, key=key) for item in value]
    return value
```

Aplica-se a todo payload retornado ( پاسso de saida) — nunca altera o
envio HTTP (não degrada contrato com a API).

## 9. Deploy

### 9.1 Script `mcp/scripts/setup_hermes_user.sh`

Cria o user Django `hermes` e imprime o DRF Token (§5.4).

### 9.2 Script `mcp/scripts/deploy_vps.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail
VPS=root@38.52.128.62
SRC=mcp/
DST=/opt/finanpy-mcp/

# 1. Validação local
python3 -c "import ast; ast.parse(open('mcp/finanpy_mcp/server.py').read())"
mcp/.venv/bin/python -m pytest mcp/tests/ -q

# 2. Sincronia (preserva .venv e .env na VPS)
rsync -avz --delete \
  --exclude='.venv' --exclude='__pycache__' --exclude='*.pyc' --exclude='.env' \
  "$SRC" "$VPS:$DST"

# 3. Reinstala deps (idempotente)
ssh "$VPS" 'cd /opt/finanpy-mcp && .venv/bin/pip install -e . -q'

# 4. Restart Hermes para re-spawn do subprocesso MCP
ssh "$VPS" 'systemctl restart hermes-gateway'

# 5. Smoke
ssh "$VPS" '/opt/finanpy-mcp/.venv/bin/python -m finanpy_mcp.smoke' \
  || { echo "Smoke falhou — verifique FINANPY_API_TOKEN no config.yaml"; exit 1; }

echo "Deploy OK"
```

### 9.3 Smoke (`mcp/finanpy_mcp/smoke.py`)

Script separado que instancia o `http_client` e dispara `health()` e
`dashboard_snapshot()`. Exita 0 em sucesso; 1 em qualquer erro.

### 9.4 Rollback

```bash
git checkout mcp/v0-direct-db -- mcp/   # reverte código
mcp/scripts/deploy_vps.sh                # redeploy
# config.yaml na VPS: command/args não mudam
```

## 10. Dependências (`pyproject.toml`)

```toml
[project]
name = "finanpy-mcp"
version = "1.1.0"
description = "MCP Server for FinanPy (Hermes agent integration)"
requires-python = ">=3.12"
dependencies = [
    "mcp[cli]>=1.0.0",
    "httpx>=0.27.0",
    "python-dotenv>=1.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "respx>=0.21.0",
]

[project.scripts]
finanpy-mcp = "finanpy_mcp.server:main"
```

> Removida `psycopg2-binary` — não há mais acesso direto ao DB.

## 11. Testes (`mcp/tests/`)

### 11.1 `test_http_client.py`

Usa `httpx.MockTransport` para simular cada caso:

- 200 → payload devolvido intacto
- 400 → `FinanPyMCPError("FinanPy rejeitou a operação: ...")`
- 401 → `FinanPyMCPError("Token FinanPy inválido ou expirado.")`
- 500 → `FinanPyMCPError("FinanPy API erro HTTP 500.")`
- Timeout → `FinanPyMCPError("Tempo esgotado ...")`
- Bearer enviado em todo request
- `follow_redirects=False`
- `Accept: application/json`, `User-Agent: Hermes/FinanPyMCP 1.1`
- Timeout 20s

### 11.2 `test_sanitization.py`

- Dict aninhado com `token`, `authorization`, `password`, `api_key` →
  redados
- Valores normais preservados
- Níveis de aninhamento recursivos

### 11.3 `test_tools_contract.py`

Usa `respx` para mock httpx por ferramenta. Assegura:

- `dashboard_snapshot()` sem `include` → apenas totals +
  recent_transactions
- `dashboard_snapshot(include="budgets,goals,chart_6m")` → todos
  presentes
- `register_quick_transaction` sem `client_id` → uuid gerado e enviado
- `register_quick_transaction` com `client_id` explícito → repassado
- Erro 400 da API → `{ok:false, error:...}`, não exception
- Lista paginada DRF → MCP retorna `payload.results`
- `confirm_pending_transaction(id=42)` → path
  `/transactions/42/confirm/`
- `create_tag(name="ALMOXO")` → envia `almox` (lower/strip)
- `create_category(category_type="INVALIDO")` → `{ok:false}`
- `update_category(id=5, is_active=False)` → PATCH com
  `{"is_active": false}`
- `list_subcategories(parent_id=2)` → só filhas
- `list_subcategories()` → árvore completa
- `add_goal_contribution(goal_id=3, amount="100")` → POST
  `/goal-contributions/` com `{"goal":3, "amount":"100", "date":<hoje>}`

### 11.4 Smoke VPS (fora do pytest)

`mcp/finanpy_mcp/smoke.py` roda em produção pós-deploy: `health()` e
`dashboard_snapshot()`. Exita 0/1.

## 12. Ordem de execução (alto nível)

Será detalhada em plano de implementação (writing-plans skill após aprovação da spec).

1. Patch `MonthlyPlanViewSet.get_queryset` (Django) + testes Django
2. Cria user `hermes` na VPS + gera DRF Token
3. Git tag `mcp/v0-direct-db` antes do rewrite
4. Refatora `mcp/finanpy_mcp/`: `server.py` (FastMCP), `config.py`,
   `http_client.py`, `sanitization.py`, `smoke.py`
5. Implementa 19 tools em `tools/`
6. Atualiza `pyproject.toml`, `.env.example`, `HERMES_CONFIG.md`
7. Implementa testes pytest (`respx` + `httpx.MockTransport`)
8. Cria `mcp/scripts/deploy_vps.sh` e `setup_hermes_user.sh`
9. Atualiza `config.yaml` na VPS
10. Deploy + smoke + teste manual via Hermes

## 13. Riscos e pendências

| Risco | Mitigação |
|---|---|
| DRF Token dá todas as permissões do user `hermes` (não há scope) | v1 assume isolamento do user; v2 avalia `IntegrationApiKey` com scopes (padrão brabus) |
| `register_quick_transaction` sem validação de faixa de amount no MCP | Backend já valida via `QuickTransactionSerializer`. MCP só repassa. |
| Transação via MCP não dispara signals de saldo | Falso — passa pela API, sinais rodam normalmente |
| `MonthlyPlanViewSet` não filtra por `year/month` | Pequeno patch Django entra no mesmo PR |
| Dados reais expostos a prompts do Hermes | Token isolado no config; só Neo principal |
| `FINANPY_API_TOKEN` sem rotatividade automática | Documentar rotacionamento manual em `HERMES_CONFIG.md` |
| Sprint 8 (PWA/mobile-first) pode mexer em endpoints | v1 usa endpoints estáveis (api/urls.py); conflitos em code review |

## 14. Out of scope (não fazer nesta spec)

- Criação/edição de accounts via MCP
- Criação/edição de budgets/goals/plans via MCP
- `POST /transactions/from-receipt/` (OCR Google Vision) — Sprint 8
- `GET /sync/since/` — é para service worker, não para agente
- Integration API com scopes (v2 futura)
- UX administrativa para gerar/revogar DRF Token (v2 — futuro)
- Testes end-to-end com LLM real

## 15. Arquivos a tocar

### Novos

```
mcp/finanpy_mcp/server.py                         (rewrite)
mcp/finanpy_mcp/config.py                         (rewrite)
mcp/finanpy_mcp/http_client.py                    (new)
mcp/finanpy_mcp/sanitization.py                   (new)
mcp/finanpy_mcp/smoke.py                          (new)
mcp/finanpy_mcp/tools/health.py                   (new)
mcp/finanpy_mcp/tools/accounts.py                 (rewrite)
mcp/finanpy_mcp/tools/categories.py               (rewrite: +create/update/list_sub)
mcp/finanpy_mcp/tools/tags.py                     (new)
mcp/finanpy_mcp/tools/transactions.py             (rewrite: quick+confirm)
mcp/finanpy_mcp/tools/reports.py                  (rewrite: dashboard_snapshot)
mcp/finanpy_mcp/tools/budgets.py                  (rewrite: list)
mcp/finanpy_mcp/tools/goals.py                    (rewrite: list+contribution)
mcp/finanpy_mcp/tools/plans.py                    (rewrite: get_monthly_plan)
mcp/finanpy_mcp/client.py                          (DELETE — não mais DB)
mcp/pyproject.toml                                (update deps)
mcp/.env.example                                  (update)
mcp/HERMES_CONFIG.md                              (update)
mcp/scripts/deploy_vps.sh                         (new)
mcp/scripts/setup_hermes_user.sh                  (new)
mcp/tests/test_http_client.py                     (new)
mcp/tests/test_sanitization.py                    (new)
mcp/tests/test_tools_contract.py                  (new)
```

### Modificados

```
api/views.py                                      (patch MonthlyPlanViewSet.get_queryset: +8 linhas para filtrar year/month)
api/tests.py                                      (test do novo filtro do MonthlyPlan)
docs/superpowers/specs/2026-07-24-mcp-finanpy-v1.1-design.md  (este arquivo)
```

### Aposentados

```
mcp/finanpy_mcp/client.py                         (arquivo deletado — acesso direto ao DB)
mcp/finanpy_mcp/tools/__pycache__/*.pyc           (limpo)
docs/superpowers/specs/2026-06-06-mcp-finanpy-design.md  (marcar como superseded sem precisar mover o arquivo de lugar — deixado no lugar para histórico)
```

## 16. Git tag

Antes de iniciar o rewrite em `mcp/`:

```bash
git tag mcp/v0-direct-db
```

Restaura o estado atual em caso de rollback.