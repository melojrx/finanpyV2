# Patrimônio, Reservas, Transferências e Valores a Receber Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Separar caixa operacional, reservas e valores a receber sem lançar movimentos patrimoniais como receitas ou despesas.

**Architecture:** `Transaction` continua sendo a única origem do fluxo operacional. `accounts` controla saldos, transferências e ajustes auditáveis; um novo app `receivables` controla empréstimos e liquidações. Serviços de domínio executam cada movimento sob `transaction.atomic()` e locks de linha, enquanto DRF e MCP apenas validam e chamam esses serviços.

**Tech Stack:** Python 3.13, Django 5.2, Django REST Framework, SQLite/PostgreSQL, FastMCP, httpx, pytest/respx, Django TestCase.

## Global Constraints

- Preserve todas as `Transaction` existentes e seus sinais de saldo.
- Não crie migrations de dados pessoais; operações iniciais ocorrem pós-release via API/MCP idempotente.
- Todo recurso é isolado por `request.user`; nenhuma rota de escrita é anônima.
- Valores monetários usam `Decimal`, duas casas e valor estritamente positivo onde aplicável.
- `available_cash` inclui exclusivamente `checking`; `net_worth` inclui todos os blocos definidos na spec.
- `savings` representa reserva remunerada; não adicionar CDI, cotação, IR, produto ou rendimento automático.
- `client_id` repetido com o mesmo payload retorna o recurso original; com payload diferente retorna HTTP 409.
- Preservar `User-Agent: Hermes/FinanPyMCP 1.1` no cliente MCP.

---

## File Structure

| Arquivo | Responsabilidade |
|---|---|
| `accounts/models.py` | Campos idempotentes, ajuste e evolução de transferência |
| `accounts/services.py` | Movimentos atômicos de conta e conflitos de idempotência |
| `accounts/admin.py` | Auditoria administrativa de transferências e ajustes |
| `receivables/models.py` | Ativo a receber e eventos de liquidação |
| `receivables/services.py` | Criação, liquidação e baixa por perda atômicas |
| `receivables/apps.py`, `admin.py` | Registro Django e auditoria |
| `api/serializers.py` | Contratos e validações DRF |
| `api/views.py`, `api/urls.py` | ViewSets, actions e rotas REST |
| `users/views.py`, `templates/dashboard/dashboard.html` | Blocos patrimoniais do dashboard web |
| `mcp/finanpy_mcp/tools/*.py` | Ferramentas MCP por domínio |
| `api/tests.py`, `accounts/tests.py`, `receivables/tests.py`, `mcp/tests/*` | Regressão, atomicidade, contrato e idempotência |

## Task 1: Freeze the current financial invariants

**Files:**
- Modify: `api/tests.py`
- Modify: `accounts/tests.py`
- Test: `api.tests.AccountTransferEndpointTests`, `api.tests.DashboardSnapshotTests`

- [ ] Add regression tests proving that a `FundTransfer` changes two balances and creates no `Transaction`.
- [ ] Add regression tests proving that `Transaction.get_monthly_summary()` excludes transfers.
- [ ] Run `.venv/bin/python manage.py test api.tests.AccountTransferEndpointTests api.tests.DashboardSnapshotTests accounts.tests --verbosity 1`.
- [ ] Commit: `test: freeze transfer and dashboard invariants`.

## Task 2: Add auditable account adjustments and strict idempotency

**Files:**
- Modify: `accounts/models.py`
- Create: `accounts/services.py`
- Create: `accounts/migrations/0004_account_balance_adjustment_and_idempotency.py`
- Modify: `accounts/admin.py`
- Test: `accounts/tests.py`

**Interfaces:**

```python
def adjust_account_balance(*, user, account_id: int, new_balance: Decimal,
                           adjustment_date: date, reason: str,
                           client_id: str) -> AccountBalanceAdjustment: ...
```

- [ ] Write failing tests for savings adjustment, investment adjustment, checking rejection, repeated `client_id`, payload conflict, and concurrent-safe old/new balances.
- [ ] Add `AccountBalanceAdjustment` with immutable previous/new/delta fields and a `(user, client_id)` uniqueness constraint.
- [ ] Add `client_id` and `destination_context` to `FundTransfer`; add a unique conditional constraint for non-empty `client_id` scoped to user.
- [ ] Implement `adjust_account_balance` with `atomic`, `select_for_update`, payload fingerprint comparison, history persistence and balance update.
- [ ] Register `FundTransfer` and `AccountBalanceAdjustment` as read-only audit objects in Django admin.
- [ ] Run `.venv/bin/python manage.py makemigrations --check --dry-run` and the accounts test module.
- [ ] Commit: `feat: add audited account balance adjustments`.

## Task 3: Promote transfers to a first-class REST resource

**Files:**
- Modify: `api/serializers.py`
- Modify: `api/views.py`
- Modify: `api/urls.py`
- Modify: `api/tests.py`

**Interfaces:**

```text
POST /api/v1/transfers/
GET  /api/v1/transfers/?account=&date_from=&date_to=
POST /api/v1/accounts/transfer/  # compatibility alias
```

- [ ] Write failing API tests for new field aliases, filters, idempotent retry, conflicting retry and user isolation.
- [ ] Add `TransferSerializer` mapping public `source_account`/`target_account` to legacy model fields.
- [ ] Make transfer creation call the service and return 201 on first write or 200 on identical retry.
- [ ] Preserve the old endpoint with a serializer adapter for `from_account`/`to_account`.
- [ ] Add `fee` support only when `fee_category` is supplied; create its confirmed `Transaction(EXPENSE)` in the same atomic service and verify it is the sole report impact.
- [ ] Run `.venv/bin/python manage.py test api.tests.AccountTransferEndpointTests --verbosity 1`.
- [ ] Commit: `feat: expose idempotent transfers API`.

## Task 4: Implement loans receivable as a bounded domain app

**Files:**
- Create: `receivables/__init__.py`, `apps.py`, `models.py`, `services.py`, `admin.py`, `tests.py`
- Create: `receivables/migrations/0001_initial.py`
- Modify: `core/settings.py`

**Interfaces:**

```python
def create_loan_receivable(*, user, counterparty: str, amount: Decimal,
                           origin_account_id: int, loan_date: date,
                           description: str, expected_return_date: date | None,
                           client_id: str) -> LoanReceivable: ...
def settle_loan_receivable(*, user, loan_id: int, amount: Decimal,
                           target_account_id: int, settlement_date: date,
                           description: str, client_id: str) -> LoanSettlement: ...
def write_off_loan_receivable(*, user, loan_id: int, reason: str) -> LoanReceivable: ...
```

- [ ] Write failing tests for creation, partial settlement, full settlement, over-settlement rejection, cross-user accounts, repeated client IDs and write-off.
- [ ] Implement `LoanReceivable` and `LoanSettlement` with decimal validation, statuses and indexes.
- [ ] Implement services with deterministic locks: loan then involved account; creation debits origin, settlement credits destination, write-off changes only the asset state.
- [ ] Register models in admin with readonly monetary history and settlement inline/list.
- [ ] Run `.venv/bin/python manage.py test receivables --verbosity 1`.
- [ ] Commit: `feat: add loans receivable domain`.

## Task 5: Expose receivables and safe account writes through DRF

**Files:**
- Modify: `api/serializers.py`
- Modify: `api/views.py`
- Modify: `api/urls.py`
- Modify: `api/tests.py`

- [ ] Write failing endpoint tests for create/list/settle/write-off and permission failures.
- [ ] Add `opening_balance` write-only to account creation; reject `balance` on account update.
- [ ] Add account adjustment list/create actions.
- [ ] Add `LoanReceivableViewSet`, status filter, settlement action and write-off action.
- [ ] Return `409 Conflict` rather than generic validation failure for client-id payload conflicts.
- [ ] Run `.venv/bin/python manage.py test api --verbosity 1`.
- [ ] Commit: `feat: expose receivables and reserve adjustments API`.

## Task 6: Calculate and render the patrimony snapshot

**Files:**
- Modify: `api/views.py`
- Modify: `api/tests.py`
- Modify: `users/views.py`
- Modify: `templates/dashboard/dashboard.html`
- Modify: `users/tests.py` or add dashboard view tests in the existing project test module

- [ ] Write failing API and web tests with checking, savings, investment, receivable, cash and negative credit-card fixtures.
- [ ] Implement one shared query helper returning `available_cash`, `reserves`, `receivables`, `unclassified_account_balance` and `net_worth`.
- [ ] Add `patrimony` to `DashboardSnapshotView` without removing existing `totals` fields.
- [ ] Replace the web “Saldo total” card with distinct Caixa disponível, Reservas, Valores a receber and Patrimônio líquido cards, following existing mobile-first card styles.
- [ ] Verify that transfer/loan records do not enter the recent `Transaction` list or monthly charts.
- [ ] Run `.venv/bin/python manage.py test api users --verbosity 1`.
- [ ] Commit: `feat: show patrimony blocks on dashboard`.

## Task 7: Extend MCP tools and transaction controls

**Files:**
- Modify: `mcp/finanpy_mcp/tools/accounts.py`
- Create: `mcp/finanpy_mcp/tools/transfers.py`
- Create: `mcp/finanpy_mcp/tools/loans_receivable.py`
- Modify: `mcp/finanpy_mcp/tools/transactions.py`
- Modify: `mcp/finanpy_mcp/server.py`
- Modify: `mcp/finanpy_mcp/tools/reports.py`
- Create: `mcp/tests/test_tools_transfers.py`
- Create: `mcp/tests/test_tools_loans_receivable.py`
- Modify: `mcp/tests/test_tools_health_accounts.py`
- Modify: `mcp/tests/test_tools_transactions_*.py`

- [ ] Write respx tests for every requested tool, generated client IDs, API error normalization and preservation of the Hermes User-Agent.
- [ ] Add account create/update/adjust tools with explicit `client_id` for adjustment.
- [ ] Add create/list transfer tools with `client_id`, context and date filters.
- [ ] Add create/list/settle/write-off loan tools.
- [ ] Add transaction PATCH and DELETE wrappers; require an explicit transaction ID and return the backend response.
- [ ] Update the snapshot tool docstring for the `patrimony` response.
- [ ] Run `cd mcp && .venv/bin/python -m pytest -q`.
- [ ] Commit: `feat: expose patrimony operations through MCP`.

## Task 8: Verify migrations, integrated behavior and release gates

**Files:**
- Modify: `mcp/finanpy_mcp/smoke.py` if its current smoke contract can assert the new read-only snapshot shape
- Modify: `docs/README.md` only to document delivered API capability after implementation

- [ ] Run `.venv/bin/python manage.py makemigrations --check --dry-run`.
- [ ] Run `.venv/bin/python manage.py test --verbosity 1`.
- [ ] Run `cd mcp && .venv/bin/python -m pytest -q`.
- [ ] Run `.venv/bin/python manage.py check` and production `check --deploy` using the CI-equivalent non-secret environment.
- [ ] Deploy through the existing immutable-image workflow; apply schema migration before accepting writes.
- [ ] Authenticate MCP against the deployed API and verify the snapshot plus a non-mutating list request.
- [ ] With human confirmation of account IDs and live balances, create the Cofre, R$49,90 resgate and R$600 empréstimo with stable client IDs; reread balances, monthly summary and snapshot.
- [ ] Commit documentation only after the implementation is complete: `docs: document patrimony operations`.

## Spec Coverage Check

- Cofre como reserva `savings`: Tasks 2, 5 e 6.
- Transferência sem receita/despesa, com idempotência: Tasks 1–3.
- Ajuste auditável: Tasks 2 e 5.
- Empréstimos, liquidação e perda: Tasks 4 e 5.
- Três blocos patrimoniais e patrimônio líquido: Task 6.
- Tools MCP solicitadas, autenticação e User-Agent: Task 7.
- Dados existentes preservados e operações iniciais controladas: Task 8.
