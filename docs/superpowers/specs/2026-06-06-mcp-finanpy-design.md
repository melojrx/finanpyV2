# MCP FinanPy Server — Especificação de Design

> Status: Draft
> Criado: 2026-06-06
> Autor: Neo/Claude

## 1. Visão Geral

**O que é:** MCP Server que expõe tools do FinanPy para o Hermes Agent via protocolo MCP (JSON-RPC over stdio).

**Por que:** Substituir chamadas HTTP diretas (risk de token exposto, sem typing, sem tool naming) por tools nomeadas com schemas definidos.

**Fluxo:**
1. Dev local (Acer Nitro) → testes OK
2. GitHub Actions → deploy para VPS
3. Hermes configura → Neo + agente-braba usam

---

## 2. Arquitetura

```
┌─────────────────────────────────────────────────────────┐
│  Hermes Agent (VPS)                                     │
│  └── MCP Client (built-in)                             │
│         │                                               │
│         │ stdio (JSON-RPC)                             │
│         ▼                                               │
│  ┌─────────────────────────────────────────────────┐   │
│  │  MCP FinanPy Server (Python 3.12)              │   │
│  │  tools/                                         │   │
│  │  ├── accounts.py     → finanpy_get_accounts    │   │
│  │  ├── transactions.py → finanpy_register_tx    │   │
│  │  ├── categories.py   → finanpy_get_categories  │   │
│  │  ├── budgets.py     → finanpy_get_budgets      │   │
│  │  ├── goals.py       → finanpy_get_goals        │   │
│  │  ├── plans.py       → finanpy_get_plan          │   │
│  │  └── reports.py     → finanpy_monthly_summary   │   │
│  └─────────────────────────────────────────────────┘   │
│                     │                                  │
│                     │ Django ORM                       │
│                     ▼                                  │
│  ┌─────────────────────────────────────────────────┐   │
│  │  FinanPy PostgreSQL                             │   │
│  │  (VPS: finanpy-db-1 / Local: SQLite dev)       │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

---

## 3. Estrutura de Diretórios

```
mcp/
├── run_mcp.py              # Entry point (mcp.server.run)
├── pyproject.toml          # Dependências + build
├── .env.example            # FINANPY_TOKEN template
├── finanpy_mcp/
│   ├── __init__.py
│   ├── server.py           # Server class + tool registry
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── accounts.py     # Account tools
│   │   ├── transactions.py # Transaction tools
│   │   ├── categories.py   # Category tools
│   │   ├── budgets.py     # Budget tools
│   │   ├── goals.py        # Goal tools
│   │   ├── plans.py        # MonthlyPlan tools
│   │   └── reports.py      # Report tools
│   ├── client.py           # Django ORM wrapper
│   └── config.py           # Token + settings
└── tests/
    ├── __init__.py
    ├── conftest.py         # Fixtures
    ├── test_accounts.py
    ├── test_transactions.py
    ├── test_categories.py
    ├── test_budgets.py
    ├── test_goals.py
    ├── test_plans.py
    └── test_reports.py
```

---

## 4. Tools Expostas

### 4.1 Accounts

| Tool | Input | Output |
|---|---|---|
| `finanpy_get_accounts` | — | `[{id, name, balance, account_type}]` |
| `finanpy_transfer` | `from_account, to_account, amount, description?, date?` | `{transfer_id, from_balance, to_balance}` |

### 4.2 Transactions

| Tool | Input | Output |
|---|---|---|
| `finanpy_register_transaction` | `type, amount, description, date?, account?, category` | `{id, balance}` |
| `finanpy_get_transactions` | `year?, month?, account?, type?, category?, limit?` | `[{id, date, type, amount, description, category}]` |
| `finanpy_confirm_pending` | `transaction_id` | `{id, status, balance}` |
| `finanpy_delete_transaction` | `transaction_id` | `{deleted: true}` |

### 4.3 Categories

| Tool | Input | Output |
|---|---|---|
| `finanpy_get_categories` | `type? (INCOME/EXPENSE)` | `[{id, name, parent_name, icon}]` |

### 4.4 Budgets

| Tool | Input | Output |
|---|---|---|
| `finanpy_get_budgets` | `year?, month?` | `[{category, planned, spent, percentage}]` |
| `finanpy_get_budget_status` | `category_id, year?, month?` | `{planned, spent, remaining, percentage}` |

### 4.5 Goals

| Tool | Input | Output |
|---|---|---|
| `finanpy_get_goals` | `—` | `[{id, name, target, current, percentage, deadline}]` |
| `finanpy_add_contribution` | `goal_id, amount, date?` | `{goal_id, new_balance, total_contributed}` |

### 4.6 Monthly Plans

| Tool | Input | Output |
|---|---|---|
| `finanpy_get_monthly_plan` | `year, month` | `{id, status, renda, teto, items}` |
| `finanpy_create_monthly_plan` | `year, month, renda_prevista, teto_despesas, items[]` | `{id, status}` |
| `finanpy_upsert_plan_item` | `year, month, category, planned_amount` | `{id, amount}` |

### 4.7 Reports

| Tool | Input | Output |
|---|---|---|
| `finanpy_monthly_summary` | `year, month` | `{income, expenses, balance, count}` |
| `finanpy_yearly_summary` | `year` | `[{month, income, expenses, balance}]` |
| `finanpy_pending_transactions` | `due?` | `[{id, date, amount, description}]` |

---

## 5. Configuração

### 5.1 Variáveis de Ambiente

```bash
# .env (local dev)
FINANFY_TOKEN=fe7dd23a50a8399a5b8731d17dbd6d8779fb30dc

# Local dev: SQLite (mesmo db.sqlite3 do FinanPy)
FINANFY_USE_SQLITE=true
FINANFY_DB_PATH=/home/jrmelo/Projetos/finanpy_v2/db.sqlite3

# Produção VPS: PostgreSQL
FINANFY_DB_HOST=127.0.0.1
FINANFY_DB_PORT=5432
FINANFY_DB_NAME=finanpy
FINANFY_DB_USER=finanpy
FINANFY_DB_PASSWORD=xxx
```

### 5.2 Hermes config (VPS)

```yaml
# /home/hermes-admin/.hermes/config.yaml (Neo principal)
mcp_servers:
  finanpy:
    command: /opt/finanpy-mcp/.venv/bin/python
    args: [/opt/finanpy-mcp/run_mcp.py]
    env:
      FINANFY_TOKEN: fe7dd23a50a8399a5b8731d17dbd6d8779fb30dc
      FINANFY_USE_SQLITE: false
      FINANFY_DB_HOST: 127.0.0.1
      FINANFY_DB_PORT: 5432

# Profile agente-braba: NÃO acessa MCP FinanPy (outro escopo)
# /home/hermes-admin/.hermes/profiles/agente-braba/config.yaml
# (sem mcp_servers.finanpy)
```

---

## 6. Fluxo de Desenvolvimento

### 6.1 Local (Acer Nitro) — SQLite

```bash
# 1. Setup
cd /home/jrmelo/Projetos/finanpy_v2/mcp
python -m venv .venv
source .venv/bin/activate
pip install -e .

# 2. Configurar .env (SQLite local, mesmo db.sqlite3 do FinanPy)
cp .env.example .env
# FINANFY_USE_SQLITE=true
# FINANFY_DB_PATH=/home/jrmelo/Projetos/finanpy_v2/db.sqlite3

# 3. Testar server (stdio mode)
python run_mcp.py

# 4. Rodar testes
pytest tests/ -v

# 5. Testar com Hermes local
# No Hermes config.yaml:
mcp_servers:
  finanpy:
    command: /home/jrmelo/Projetos/finanpy_v2/mcp/.venv/bin/python
    args: [/home/jrmelo/Projetos/finanpy_v2/mcp/run_mcp.py]
```

**Nota:** SQLite local pode ter dados desatualizados vs produção VPS. Para testes de lógica é suficiente. Para testes de dados reais, usar MPS (futuro)."

### 6.2 GitHub Actions (deploy)

```yaml
# .github/workflows/mcp-deploy.yml
name: Deploy MCP FinanPy to VPS

on:
  push:
    branches: [main]
    paths: ['mcp/**']

jobs:
  deploy-mcp:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Deploy via SSH
        uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.VPS_HOST }}
          username: root
          key: ${{ secrets.VPS_DEPLOY_KEY }}
          script: |
            # Pull latest
            cd /opt/finanpy-mcp
            git pull

            # Recreate venv
            rm -rf .venv
            python3.12 -m venv .venv
            .venv/bin/pip install -e .

            # Restart Hermes
            systemctl restart hermes-gateway hermes-gateway-agente-braba
```

### 6.3 VPS (pós deploy)

```bash
# Arquivos devem estar em:
/opt/finanpy-mcp/

# Configurar Hermes (manual ou via script)
/home/hermes-admin/.hermes/config.yaml
/home/hermes-admin/.hermes/profiles/agente-braba/config.yaml

# Restart services
sudo systemctl restart hermes-gateway hermes-gateway-agente-braba

# Verificar logs
journalctl -u hermes-gateway -f | grep -i finanpy
```

---

## 7. Error Handling

| Erro | Código | Ação |
|---|---|---|
| Token inválido | `AUTH_ERROR` | Retornar erro + instrução para verificar token |
| Category not found | `NOT_FOUND` | Retornar lista de categorias válidas como hint |
| Validation error | `VALIDATION_ERROR` | Retornar campo específico + formato esperado |
| DB connection fail | `CONNECTION_ERROR` | Retry 1x, depois falhar com mensagem clara |

---

## 8. Segurança

- **Token** em `.env` (não commitado)
- **DB connection** via `127.0.0.1` (não exposto externamente)
- **Hermes config** owner `hermes-admin`, mode `600`
- **Nenhuma tool faz DELETE em cascata** — apenas soft delete ou confirmação

---

## 9. Dependências

```toml
[project]
name = "finanpy-mcp"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "mcp>=0.9.0",
    "psycopg2-binary>=2.9.9",
    "python-dotenv>=1.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
]
```

---

## 10. Testes

```bash
# Unit tests por module
pytest tests/ -v

# Integration test (mock Hermes)
pytest tests/test_integration.py -v

# Smoke test (server starts)
python run_mcp.py --help  # quick check
```

---

## 11. Checklist de Implementação

- [ ] Setup projeto (pyproject.toml, venv)
- [ ] Config module (env loading)
- [ ] Django ORM client (base)
- [ ] Tools: accounts
- [ ] Tools: transactions
- [ ] Tools: categories
- [ ] Tools: budgets
- [ ] Tools: goals
- [ ] Tools: plans
- [ ] Tools: reports
- [ ] Server entry point
- [ ] Unit tests (todos)
- [ ] Local smoke test
- [ ] GitHub Actions workflow
- [ ] Hermes config (neo + agente-braba)
- [ ] VPS deploy + validation

---

## 12. Arquivos a criar

```
mcp/
├── run_mcp.py
├── pyproject.toml
├── .env.example
├── finanpy_mcp/
│   ├── __init__.py
│   ├── server.py
│   ├── config.py
│   ├── client.py
│   └── tools/
│       ├── __init__.py
│       ├── accounts.py
│       ├── transactions.py
│       ├── categories.py
│       ├── budgets.py
│       ├── goals.py
│       ├── plans.py
│       └── reports.py
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── test_accounts.py
    ├── test_transactions.py
    ├── test_categories.py
    ├── test_budgets.py
    ├── test_goals.py
    ├── test_plans.py
    └── test_reports.py

.github/
└── workflows/
    └── mcp-deploy.yml
```