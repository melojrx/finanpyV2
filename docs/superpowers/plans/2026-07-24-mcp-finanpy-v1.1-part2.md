# MCP FinanPy v1.1 — Plano de Implementação (Parte 2/3)

> Continuação de Parte 1/3. Ler Parte 1 primeiro.

**Goal desta parte:** Implementar 12 tools de leitura (health, accounts, categories, subcategories, tags, transactions list, dashboard_snapshot, monthly_summary, yearly_summary, budgets, goals, plans).

---

## Task 7: Helpers — _result, _filter_params, _safe_call

**Files:**
- Create: `mcp/finanpy_mcp/helpers.py`
- Test: `mcp/tests/test_helpers.py`

- [ ] **Step 1: Write the failing test**

Criar `mcp/tests/test_helpers.py`:

```python
import pytest
from finanpy_mcp.helpers import _result, _filter_params, _safe_call, _clean_text, _safe_int
from finanpy_mcp.http_client import FinanPyMCPError


def test_result_basic():
    r = _result("accounts", {"id": 1})
    assert r == {"ok": True, "endpoint": "accounts", "params": {}, "payload": {"id": 1}}


def test_result_with_params():
    r = _result("accounts", {"id": 1}, params={"type": "INCOME"})
    assert r["params"] == {"type": "INCOME"}


def test_filter_params_removes_none():
    out = _filter_params({"a": 1, "b": None, "c": "x", "d": 0})
    assert out == {"a": 1, "c": "x", "d": 0}


def test_filter_params_empty():
    assert _filter_params({"a": None}) == {}


def test_safe_call_success():
    def fn():
        return {"ok": True}
    assert _safe_call(fn) == {"ok": True}


def test_safe_call_catches_error():
    def fn():
        raise FinanPyMCPError("Boom")
    r = _safe_call(fn)
    assert r["ok"] is False
    assert "Boom" in r["error"]


def test_clean_text_strips_and_truncates():
    assert _clean_text("  hello  ") == "hello"
    assert _clean_text("x" * 200, max_len=10) == "xxxxxxxxxx"


def test_safe_int():
    assert _safe_int(5, default=1, min_value=1, max_value=100) == 5
    assert _safe_int("abc", default=10, min_value=1, max_value=100) == 10
    assert _safe_int(0, default=1, min_value=1, max_value=100) == 1
    assert _safe_int(999, default=1, min_value=1, max_value=100) == 100
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd mcp && .venv/bin/python -m pytest tests/test_helpers.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'finanpy_mcp.helpers'`

- [ ] **Step 3: Write minimal implementation**

Criar `mcp/finanpy_mcp/helpers.py`:

```python
"""Shared helpers for MCP tools."""
from typing import Any, Callable

from .http_client import FinanPyMCPError
from .sanitization import sanitize_payload


def _result(endpoint: str, payload: Any, params: dict | None = None) -> dict:
    """Build a standardized success response."""
    return {
        "ok": True,
        "endpoint": endpoint,
        "params": sanitize_payload(params or {}),
        "payload": sanitize_payload(payload),
    }


def _filter_params(d: dict) -> dict:
    """Remove keys with None values, preserving 0 and False."""
    return {k: v for k, v in d.items() if v is not None}


def _safe_call(fn: Callable) -> dict:
    """Execute fn, catching FinanPyMCPError and returning a dict in either case."""
    try:
        return fn()
    except FinanPyMCPError as e:
        return {"ok": False, "error": str(e)}


def _clean_text(value: str, *, max_len: int = 120) -> str:
    return str(value or "").strip()[:max_len]


def _safe_int(value, *, default: int, min_value: int, max_value: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(min_value, min(max_value, parsed))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd mcp && .venv/bin/python -m pytest tests/test_helpers.py -v`
Expected: PASS — 8 testes

- [ ] **Step 5: Commit**

```bash
git add mcp/finanpy_mcp/helpers.py mcp/tests/test_helpers.py
git commit -m "feat(mcp): add helpers module (result, filter_params, safe_call, clean_text, safe_int)"
```

---

## Task 8: Health + Accounts tools

**Files:**
- Modify: `mcp/finanpy_mcp/tools/health.py` (rewrite, substituir stub)
- Modify: `mcp/finanpy_mcp/tools/accounts.py` (rewrite, substituir stub)
- Test: `mcp/tests/test_tools_health_accounts.py`

- [ ] **Step 1: Write the failing test**

Criar `mcp/tests/test_tools_health_accounts.py`:

```python
import httpx
import respx
import pytest
from finanpy_mcp.tools.health import health
from finanpy_mcp.tools.accounts import list_accounts
from finanpy_mcp.http_client import FinanPyClient


@pytest.fixture
def client():
    return FinanPyClient(
        base_url="http://test/api/v1/",
        token="t" * 40,
        timeout=5.0,
    )


@respx.mock
def test_health_ok(client):
    respx.get("http://test/api/v1/accounts/").respond(200, json={"results": []})
    r = health(client)
    assert r["ok"] is True
    assert r["endpoint"] == "health"
    assert r["payload"]["status"] == "ok"


@respx.mock
def test_health_fails_on_500(client):
    respx.get("http://test/api/v1/accounts/").respond(500, json={"error": "boom"})
    r = health(client)
    assert r["ok"] is False
    assert "HTTP 500" in r["error"]


@respx.mock
def test_list_accounts(client):
    respx.get("http://test/api/v1/accounts/").respond(200, json={
        "results": [{"id": 1, "name": "Caixa", "balance": "100.00", "account_type": "CHECKING"}]
    })
    r = list_accounts(client)
    assert r["ok"] is True
    assert r["endpoint"] == "accounts"
    assert r["payload"]["results"][0]["name"] == "Caixa"


@respx.mock
def test_list_accounts_error(client):
    respx.get("http://test/api/v1/accounts/").respond(401, json={"detail": "bad token"})
    r = list_accounts(client)
    assert r["ok"] is False
    assert "Token" in r["error"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd mcp && .venv/bin/python -m pytest tests/test_tools_health_accounts.py -v`
Expected: FAIL — `health` e `list_accounts` ainda são stubs

- [ ] **Step 3: Write minimal implementation**

Rewrite `mcp/finanpy_mcp/tools/health.py`:

```python
"""Health-related MCP tools."""
from ..helpers import _result, _safe_call


def health(client) -> dict:
    """Check FinanPy API connectivity and auth."""
    return _safe_call(lambda: client.request("GET", "accounts/")) and \
        _result("health", {"status": "ok"})


def register_health_tools(mcp, client):
    """Register health tools with MCP server."""

    @mcp.tool()
    def finanpy_health() -> dict:
        """Verifica se a API do FinanPy está acessível e o token é válido."""
        return health(client)
```

Rewrite `mcp/finanpy_mcp/tools/accounts.py`:

```python
"""Account-related MCP tools."""
from ..helpers import _result, _safe_call


def list_accounts(client) -> dict:
    """List all accounts with current balances."""
    return _safe_call(lambda: _result(
        "accounts",
        client.request("GET", "accounts/"),
    ))


def register_account_tools(mcp, client):
    """Register account tools with MCP server."""

    @mcp.tool()
    def finanpy_list_accounts() -> dict:
        """Lista todas as contas com saldos atuais.

        Returns:
            {ok, endpoint, params, payload} onde payload.results é
            [{id, name, balance, account_type}, ...]
        """
        return list_accounts(client)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd mcp && .venv/bin/python -m pytest tests/test_tools_health_accounts.py -v`
Expected: PASS — 4 testes

- [ ] **Step 5: Commit**

```bash
git add mcp/finanpy_mcp/tools/health.py mcp/finanpy_mcp/tools/accounts.py mcp/tests/test_tools_health_accounts.py
git commit -m "feat(mcp): add health and list_accounts tools"
```

---

## Task 9: Categories (list, subcategories) + Tags tools

**Files:**
- Modify: `mcp/finanpy_mcp/tools/categories.py` (rewrite)
- Modify: `mcp/finanpy_mcp/tools/tags.py` (rewrite)
- Test: `mcp/tests/test_tools_categories_tags.py`

- [ ] **Step 1: Write the failing test**

Criar `mcp/tests/test_tools_categories_tags.py`:

```python
import pytest
import respx
from finanpy_mcp.tools.categories import list_categories, list_subcategories
from finanpy_mcp.tools.tags import list_tags
from finanpy_mcp.http_client import FinanPyClient


@pytest.fixture
def client():
    return FinanPyClient(
        base_url="http://test/api/v1/",
        token="t" * 40,
        timeout=5.0,
    )


CATEGORIES_DATA = [
    {"id": 1, "name": "Alimentação", "category_type": "EXPENSE", "parent": None, "icon": "🍔"},
    {"id": 2, "name": "Restaurantes", "category_type": "EXPENSE", "parent": 1, "icon": "🍽️"},
    {"id": 3, "name": "Salário", "category_type": "INCOME", "parent": None, "icon": "💰"},
]


@respx.mock
def test_list_categories_all(client):
    respx.get("http://test/api/v1/categories/").respond(200, json={"results": CATEGORIES_DATA})
    r = list_categories(client)
    assert r["ok"] is True
    assert len(r["payload"]["results"]) == 3


@respx.mock
def test_list_categories_by_type(client):
    route = respx.get("http://test/api/v1/categories/")
    route.respond(200, json={"results": [CATEGORIES_DATA[2]]})
    r = list_categories(client, category_type="INCOME")
    assert r["ok"] is True
    assert r["params"] == {"type": "INCOME"}
    assert route.calls.last.request.url.params["type"] == "INCOME"


@respx.mock
def test_list_subcategories_by_parent(client):
    respx.get("http://test/api/v1/categories/").respond(200, json={"results": CATEGORIES_DATA})
    r = list_subcategories(client, parent_id=1)
    assert r["ok"] is True
    assert r["params"] == {"parent_id": 1}
    results = r["payload"]["results"]
    assert len(results) == 1
    assert results[0]["id"] == 2
    assert results[0]["name"] == "Restaurantes"


@respx.mock
def test_list_subcategories_no_parent_returns_tree(client):
    respx.get("http://test/api/v1/categories/").respond(200, json={"results": CATEGORIES_DATA})
    r = list_subcategories(client)
    assert r["ok"] is True
    roots = r["payload"]["results"]
    assert len(roots) == 2  # Alimentação + Salário (no parent)
    alimentacao = [c for c in roots if c["id"] == 1][0]
    assert len(alimentacao["children"]) == 1
    assert alimentacao["children"][0]["id"] == 2


@respx.mock
def test_list_tags(client):
    respx.get("http://test/api/v1/tags/").respond(200, json={
        "results": [{"id": 1, "name": "recorrente", "created_at": "2026-07-01T00:00:00Z"}]
    })
    r = list_tags(client)
    assert r["ok"] is True
    assert r["payload"]["results"][0]["name"] == "recorrente"


@respx.mock
def test_list_categories_error(client):
    respx.get("http://test/api/v1/categories/").respond(500, json={"error": "boom"})
    r = list_categories(client)
    assert r["ok"] is False
    assert "HTTP 500" in r["error"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd mcp && .venv/bin/python -m pytest tests/test_tools_categories_tags.py -v`
Expected: FAIL — stubs não implementam funções

- [ ] **Step 3: Write minimal implementation**

Rewrite `mcp/finanpy_mcp/tools/categories.py`:

```python
"""Category-related MCP tools."""
from ..helpers import _result, _safe_call, _filter_params


def list_categories(client, category_type=None) -> dict:
    """List all active categories, optionally filtered by type."""
    params = _filter_params({"type": category_type})
    return _safe_call(lambda: _result(
        "categories",
        client.request("GET", "categories/", params=params or None),
        params,
    ))


def _build_tree(cats: list) -> list:
    by_id = {c["id"]: {**c, "children": []} for c in cats if "id" in c}
    roots = []
    for c in cats:
        cid = c.get("id")
        parent = c.get("parent")
        if cid not in by_id:
            continue
        if parent and parent in by_id:
            by_id[parent]["children"].append(by_id[cid])
        elif not parent:
            roots.append(by_id[cid])
    return roots


def list_subcategories(client, parent_id=None) -> dict:
    """List subcategories (children) by parent_id, or the full tree if omitted."""
    def _do():
        payload = client.request("GET", "categories/")
        data = payload.get("results", payload) if isinstance(payload, dict) else payload
        if not isinstance(data, list):
            data = []
        if parent_id is not None:
            filtered = [c for c in data if c.get("parent") == parent_id]
            return _result("subcategories", {"results": filtered}, {"parent_id": parent_id})
        tree = _build_tree(data)
        return _result("subcategories", {"results": tree}, {})
    return _safe_call(_do)


def register_category_tools(mcp, client):
    """Register category tools with MCP server."""

    @mcp.tool()
    def finanpy_list_categories(category_type: str | None = None) -> dict:
        """Lista categorias ativas, opcionalmente filtradas por tipo.

        Args:
            category_type: "INCOME" ou "EXPENSE" (opcional)

        Returns:
            {ok, endpoint, params, payload} — payload.results é
            [{id, name, category_type, parent, color, icon, is_active}, ...]
        """
        return list_categories(client, category_type=category_type)

    @mcp.tool()
    def finanpy_list_subcategories(parent_id: int | None = None) -> dict:
        """Lista subcategorias filhas de parent_id, ou a árvore completa.

        Args:
            parent_id: ID da categoria pai (opcional). Se omitido,
                       devolve a hierarquia completa em `children`.

        Returns:
            {ok, endpoint, params, payload} — payload.results é
            [{id, name, children: [...]}, ...]
        """
        return list_subcategories(client, parent_id=parent_id)
```

Rewrite `mcp/finanpy_mcp/tools/tags.py`:

```python
"""Tag-related MCP tools."""
from ..helpers import _result, _safe_call


def list_tags(client) -> dict:
    """List all tags."""
    return _safe_call(lambda: _result(
        "tags",
        client.request("GET", "tags/"),
    ))


def register_tag_tools(mcp, client):
    """Register tag tools with MCP server."""

    @mcp.tool()
    def finanpy_list_tags() -> dict:
        """Lista todas as tags do usuário.

        Returns:
            {ok, endpoint, params, payload} — payload.results é
            [{id, name, created_at}, ...]
        """
        return list_tags(client)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd mcp && .venv/bin/python -m pytest tests/test_tools_categories_tags.py -v`
Expected: PASS — 7 testes

- [ ] **Step 5: Commit**

```bash
git add mcp/finanpy_mcp/tools/categories.py mcp/finanpy_mcp/tools/tags.py mcp/tests/test_tools_categories_tags.py
git commit -m "feat(mcp): add list_categories, list_subcategories (with tree), list_tags tools"
```

---

## Task 10: Transactions (list) tool

**Files:**
- Modify: `mcp/finanpy_mcp/tools/transactions.py` (partial — only list; write tools in Part 3)
- Test: `mcp/tests/test_tools_transactions_list.py`

- [ ] **Step 1: Write the failing test**

Criar `mcp/tests/test_tools_transactions_list.py`:

```python
import pytest
import respx
from finanpy_mcp.tools.transactions import list_transactions
from finanpy_mcp.http_client import FinanPyClient


@pytest.fixture
def client():
    return FinanPyClient(
        base_url="http://test/api/v1/",
        token="t" * 40,
        timeout=5.0,
    )


@respx.mock
def test_list_transactions_no_filters(client):
    respx.get("http://test/api/v1/transactions/").respond(200, json={
        "count": 1,
        "results": [{"id": 10, "amount": "50.00", "transaction_type": "EXPENSE"}]
    })
    r = list_transactions(client)
    assert r["ok"] is True
    assert r["params"] == {"page": 1, "page_size": 50}
    assert r["payload"]["results"][0]["id"] == 10


@respx.mock
def test_list_transactions_with_filters(client):
    route = respx.get("http://test/api/v1/transactions/")
    route.respond(200, json={"count": 0, "results": []})
    r = list_transactions(client, year=2026, month=7, transaction_type="EXPENSE", page=2, page_size=10)
    assert r["ok"] is True
    sent_params = route.calls.last.request.url.params
    assert sent_params["year"] == "2026"
    assert sent_params["month"] == "7"
    assert sent_params["type"] == "EXPENSE"
    assert sent_params["page"] == "2"
    assert sent_params["page_size"] == "10"


@respx.mock
def test_list_transactions_error(client):
    respx.get("http://test/api/v1/transactions/").respond(500, json={"error": "boom"})
    r = list_transactions(client)
    assert r["ok"] is False
    assert "HTTP 500" in r["error"]


@respx.mock
def test_list_transactions_sanitizes_in_response(client):
    respx.get("http://test/api/v1/transactions/").respond(200, json={
        "results": [{"id": 1, "token": "secret-value", "amount": "10"}]
    })
    r = list_transactions(client)
    assert r["payload"]["results"][0]["token"] == "***redacted***"
    assert r["payload"]["results"][0]["amount"] == "10"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd mcp && .venv/bin/python -m pytest tests/test_tools_transactions_list.py -v`
Expected: FAIL — `list_transactions` doesn't exist yet (transactions.py is still stub)

- [ ] **Step 3: Write minimal implementation**

Rewrite `mcp/finanpy_mcp/tools/transactions.py`:

```python
"""Transaction-related MCP tools."""
from ..helpers import _result, _safe_call, _filter_params, _safe_int


def list_transactions(
    client,
    year=None,
    month=None,
    account=None,
    transaction_type=None,
    category=None,
    status=None,
    page=1,
    page_size=50,
) -> dict:
    """List transactions with optional filters."""
    params = _filter_params({
        "year": year,
        "month": month,
        "account": account,
        "type": transaction_type,
        "category": category,
        "status": status,
        "page": _safe_int(page, default=1, min_value=1, max_value=10000),
        "page_size": _safe_int(page_size, default=50, min_value=1, max_value=100),
    })
    return _safe_call(lambda: _result(
        "transactions",
        client.request("GET", "transactions/", params=params),
        params,
    ))


def register_transaction_tools(mcp, client):
    """Register transaction tools with MCP server."""

    @mcp.tool()
    def finanpy_list_transactions(
        year: int | None = None,
        month: int | None = None,
        account: int | None = None,
        transaction_type: str | None = None,
        category: int | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> dict:
        """Lista transações com filtros opcionais.

        Args:
            year: Filtrar por ano
            month: Filtrar por mês (1-12)
            account: Filtrar por ID de conta
            transaction_type: "EXPENSE" ou "INCOME"
            category: Filtrar por ID de categoria
            status: "PENDING" ou "CONFIRMED"
            page: Página (default 1)
            page_size: Itens por página (default 50, máx 100)

        Returns:
            {ok, endpoint, params, payload} — payload.results é
            [{id, amount, transaction_type, ...}, ...] e payload.count
            tem o total de resultados.
        """
        return list_transactions(
            client,
            year=year,
            month=month,
            account=account,
            transaction_type=transaction_type,
            category=category,
            status=status,
            page=page,
            page_size=page_size,
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd mcp && .venv/bin/python -m pytest tests/test_tools_transactions_list.py -v`
Expected: PASS — 4 testes

- [ ] **Step 5: Commit**

```bash
git add mcp/finanpy_mcp/tools/transactions.py mcp/tests/test_tools_transactions_list.py
git commit -m "feat(mcp): add list_transactions tool with filters and pagination"
```

---

## Task 11: Reports — dashboard_snapshot, monthly_summary, yearly_summary

**Files:**
- Modify: `mcp/finanpy_mcp/tools/reports.py` (rewrite)
- Test: `mcp/tests/test_tools_reports.py`

- [ ] **Step 1: Write the failing test**

Criar `mcp/tests/test_tools_reports.py`:

```python
import pytest
import respx
from finanpy_mcp.tools.reports import dashboard_snapshot, monthly_summary, yearly_summary
from finanpy_mcp.http_client import FinanPyClient


@pytest.fixture
def client():
    return FinanPyClient(
        base_url="http://test/api/v1/",
        token="t" * 40,
        timeout=5.0,
    )


@respx.mock
def test_dashboard_snapshot_default(client):
    respx.get("http://test/api/v1/dashboard/snapshot/").respond(200, json={
        "totals": {"total_balance": "1000.00"},
        "recent_transactions": [],
    })
    r = dashboard_snapshot(client)
    assert r["ok"] is True
    assert r["payload"]["totals"]["total_balance"] == "1000.00"
    assert r["params"] == {}


@respx.mock
def test_dashboard_snapshot_with_include(client):
    route = respx.get("http://test/api/v1/dashboard/snapshot/")
    route.respond(200, json={"totals": {}, "budgets": [], "goals": [], "chart_6m": {}})
    r = dashboard_snapshot(client, include="budgets,goals,chart_6m")
    assert r["ok"] is True
    assert r["params"]["include"] == "budgets,goals,chart_6m"
    sent = route.calls.last.request.url.params
    assert sent["include"] == "budgets,goals,chart_6m"


@respx.mock
def test_dashboard_snapshot_error(client):
    respx.get("http://test/api/v1/dashboard/snapshot/").respond(404, json={"detail": "nope"})
    r = dashboard_snapshot(client)
    assert r["ok"] is False
    assert "não encontrado" in r["error"]


@respx.mock
def test_monthly_summary(client):
    respx.get("http://test/api/v1/summary/monthly/").respond(200, json={
        "year": 2026, "month": 7, "income": "5000.00",
        "expenses": "3000.00", "balance": "2000.00", "transaction_count": 25
    })
    r = monthly_summary(client, year=2026, month=7)
    assert r["ok"] is True
    assert r["payload"]["balance"] == "2000.00"
    assert r["params"] == {"year": 2026, "month": 7}


@respx.mock
def test_yearly_summary(client):
    respx.get("http://test/api/v1/summary/yearly/").respond(200, json={
        "year": 2026, "total_income": "60000.00",
        "total_expenses": "36000.00", "months": []
    })
    r = yearly_summary(client, year=2026)
    assert r["ok"] is True
    assert r["params"] == {"year": 2026}
    assert r["payload"]["total_income"] == "60000.00"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd mcp && .venv/bin/python -m pytest tests/test_tools_reports.py -v`
Expected: FAIL — stub

- [ ] **Step 3: Write minimal implementation**

Rewrite `mcp/finanpy_mcp/tools/reports.py`:

```python
"""Report-related MCP tools: dashboard snapshot and summaries."""
from ..helpers import _result, _safe_call, _filter_params


def dashboard_snapshot(client, include=None) -> dict:
    """Get consolidated dashboard snapshot with optional bundles."""
    params = _filter_params({"include": include})
    return _safe_call(lambda: _result(
        "dashboard/snapshot",
        client.request("GET", "dashboard/snapshot/", params=params or None),
        params,
    ))


def monthly_summary(client, year, month) -> dict:
    """Get monthly financial summary."""
    params = {"year": year, "month": month}
    return _safe_call(lambda: _result(
        "summary/monthly",
        client.request("GET", "summary/monthly/", params=params),
        params,
    ))


def yearly_summary(client, year) -> dict:
    """Get yearly financial summary."""
    params = {"year": year}
    return _safe_call(lambda: _result(
        "summary/yearly",
        client.request("GET", "summary/yearly/", params=params),
        params,
    ))


def register_report_tools(mcp, client):
    """Register report tools with MCP server."""

    @mcp.tool()
    def finanpy_dashboard_snapshot(include: str | None = None) -> dict:
        """Snapshot consolidado do dashboard (1 chamada cobre tudo).

        Args:
            include: CSV (ex.: "budgets,goals,chart_6m") para incluir
                     pacotes opcionais. Default: apenas totais + 5 recentes.

        Returns:
            {ok, endpoint, params, payload} — payload contém:
            totals {total_balance, income_month, expenses_month, balance_month,
                    savings_pct, transaction_count_month} e
            recent_transactions [{...}, ...] + optionally budgets, goals, chart_6m.
        """
        return dashboard_snapshot(client, include=include)

    @mcp.tool()
    def finanpy_monthly_summary(year: int, month: int) -> dict:
        """Resumo financeiro mensal (receitas, despesas, saldo)."""
        return monthly_summary(client, year=year, month=month)

    @mcp.tool()
    def finanpy_yearly_summary(year: int) -> dict:
        """Resumo financeiro anual (12 meses detalhados)."""
        return yearly_summary(client, year=year)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd mcp && .venv/bin/python -m pytest tests/test_tools_reports.py -v`
Expected: PASS — 5 testes

- [ ] **Step 5: Commit**

```bash
git add mcp/finanpy_mcp/tools/reports.py mcp/tests/test_tools_reports.py
git commit -m "feat(mcp): add dashboard_snapshot, monthly_summary, yearly_summary tools"
```

---

## Task 12: Budgets (list), Goals (list), Plans (get) tools

**Files:**
- Modify: `mcp/finanpy_mcp/tools/budgets.py` (rewrite)
- Modify: `mcp/finanpy_mcp/tools/goals.py` (partial — only list; contribution in Part 3)
- Modify: `mcp/finanpy_mcp/tools/plans.py` (rewrite)
- Test: `mcp/tests/test_tools_budgets_goals_plans.py`

- [ ] **Step 1: Write the failing test**

Criar `mcp/tests/test_tools_budgets_goals_plans.py`:

```python
import pytest
import respx
from finanpy_mcp.tools.budgets import list_budgets
from finanpy_mcp.tools.goals import list_goals
from finanpy_mcp.tools.plans import get_monthly_plan
from finanpy_mcp.http_client import FinanPyClient


@pytest.fixture
def client():
    return FinanPyClient(
        base_url="http://test/api/v1/",
        token="t" * 40,
        timeout=5.0,
    )


@respx.mock
def test_list_budgets_no_filters(client):
    respx.get("http://test/api/v1/budgets/").respond(200, json={
        "results": [{"id": 1, "name": "Alimentação", "planned_amount": "500.00"}]
    })
    r = list_budgets(client)
    assert r["ok"] is True
    assert r["params"] == {}
    assert r["payload"]["results"][0]["name"] == "Alimentação"


@respx.mock
def test_list_budgets_with_filters(client):
    route = respx.get("http://test/api/v1/budgets/")
    route.respond(200, json={"results": []})
    r = list_budgets(client, year=2026, month=7, active=True)
    assert r["ok"] is True
    assert r["params"] == {"year": 2026, "month": 7, "active": "true"}
    sent = route.calls.last.request.url.params
    assert sent["year"] == "2026"
    assert sent["month"] == "7"
    assert sent["active"] == "true"


@respx.mock
def test_list_goals_no_status(client):
    respx.get("http://test/api/v1/goals/").respond(200, json={
        "results": [{"id": 1, "name": "Viagem", "target_amount": "10000.00", "status": "ACTIVE"}]
    })
    r = list_goals(client)
    assert r["ok"] is True
    assert r["params"] == {}
    assert r["payload"]["results"][0]["name"] == "Viagem"


@respx.mock
def test_list_goals_with_status(client):
    route = respx.get("http://test/api/v1/goals/")
    route.respond(200, json={"results": []})
    r = list_goals(client, status="ACTIVE")
    assert r["ok"] is True
    assert r["params"] == {"status": "ACTIVE"}
    assert route.calls.last.request.url.params["status"] == "ACTIVE"


@respx.mock
def test_get_monthly_plan(client):
    respx.get("http://test/api/v1/monthly-plans/").respond(200, json={
        "results": [{"id": 42, "year": 2026, "month": 7, "status": "ACTIVE", "renda_prevista": "5000.00"}]
    })
    r = get_monthly_plan(client, year=2026, month=7)
    assert r["ok"] is True
    assert r["params"] == {"year": 2026, "month": 7}
    assert r["payload"]["results"][0]["id"] == 42


@respx.mock
def test_get_monthly_plan_empty(client):
    respx.get("http://test/api/v1/monthly-plans/").respond(200, json={"results": []})
    r = get_monthly_plan(client, year=2026, month=7)
    assert r["ok"] is True
    assert r["payload"]["results"] == []


@respx.mock
def test_budgets_error(client):
    respx.get("http://test/api/v1/budgets/").respond(401, json={"detail": "bad"})
    r = list_budgets(client)
    assert r["ok"] is False
    assert "Token" in r["error"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd mcp && .venv/bin/python -m pytest tests/test_tools_budgets_goals_plans.py -v`
Expected: FAIL — stubs

- [ ] **Step 3: Write minimal implementation**

Rewrite `mcp/finanpy_mcp/tools/budgets.py`:

```python
"""Budget-related MCP tools."""
from ..helpers import _result, _safe_call, _filter_params


def _normalize_active(active):
    if active is None:
        return None
    return "true" if active else "false"


def list_budgets(client, year=None, month=None, active=None) -> dict:
    """List budgets, optionally filtered by year/month/active."""
    params = _filter_params({
        "year": year,
        "month": month,
        "active": _normalize_active(active),
    })
    return _safe_call(lambda: _result(
        "budgets",
        client.request("GET", "budgets/", params=params or None),
        params,
    ))


def register_budget_tools(mcp, client):
    """Register budget tools with MCP server."""

    @mcp.tool()
    def finanpy_list_budgets(
        year: int | None = None,
        month: int | None = None,
        active: bool | None = None,
    ) -> dict:
        """Lista orçamentos ativos, opcionalmente filtrados por ano/mês.

        Args:
            year: Filtrar por ano
            month: Filtrar por mês (1-12)
            active: True para apenas ativos; False para inativos; None para todos

        Returns:
            {ok, endpoint, params, payload} — payload.results é
            [{id, name, planned_amount, spent_amount, category, ...}, ...]
        """
        return list_budgets(client, year=year, month=month, active=active)
```

Rewrite `mcp/finanpy_mcp/tools/goals.py`:

```python
"""Goal-related MCP tools."""
from ..helpers import _result, _safe_call, _filter_params


def list_goals(client, status=None) -> dict:
    """List savings goals, optionally filtered by status."""
    params = _filter_params({"status": status})
    return _safe_call(lambda: _result(
        "goals",
        client.request("GET", "goals/", params=params or None),
        params,
    ))


def register_goal_tools(mcp, client):
    """Register goal tools with MCP server."""

    @mcp.tool()
    def finanpy_list_goals(status: str | None = None) -> dict:
        """Lista metas financeiras, opcionalmente filtradas por status.

        Args:
            status: "ACTIVE", "COMPLETED" ou "CANCELLED" (opcional)

        Returns:
            {ok, endpoint, params, payload} — payload.results é
            [{id, name, target_amount, current_amount, progress_pct,
              status, deadline, ...}, ...]
        """
        return list_goals(client, status=status)
```

Rewrite `mcp/finanpy_mcp/tools/plans.py`:

```python
"""Monthly plan-related MCP tools."""
from ..helpers import _result, _safe_call


def get_monthly_plan(client, year, month) -> dict:
    """Get the monthly plan for a given year/month."""
    params = {"year": year, "month": month}
    return _safe_call(lambda: _result(
        "monthly-plans",
        client.request("GET", "monthly-plans/", params=params),
        params,
    ))


def register_plan_tools(mcp, client):
    """Register monthly plan tools with MCP server."""

    @mcp.tool()
    def finanpy_get_monthly_plan(year: int, month: int) -> dict:
        """Obtém o plano mensal (orçamento planejado) de um mês/ano.

        Args:
            year: Ano (ex.: 2026)
            month: Mês (1-12)

        Returns:
            {ok, endpoint, params, payload} — payload.results é
            [{id, year, month, status, renda_prevista, teto_despesas,
              renda_realizada, despesas_realizadas, saldo_disponivel, ...}]
        """
        return get_monthly_plan(client, year=year, month=month)
```

> Note: `goals.py` will gain `add_goal_contribution` in Part 3. Keep the file
> structure ready — just append the function later.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd mcp && .venv/bin/python -m pytest tests/test_tools_budgets_goals_plans.py -v`
Expected: PASS — 7 testes

- [ ] **Step 5: Run full MCP test suite to verify integration**

Run: `cd mcp && .venv/bin/python -m pytest tests/ -v`
Expected: PASS — all tests across Parte 1 + Parte 2

- [ ] **Step 6: Commit**

```bash
git add mcp/finanpy_mcp/tools/budgets.py mcp/finanpy_mcp/tools/goals.py mcp/finanpy_mcp/tools/plans.py mcp/tests/test_tools_budgets_goals_plans.py
git commit -m "feat(mcp): add list_budgets, list_goals, get_monthly_plan tools"
```

---

## Fim da Parte 2

Todas as 12 tools de leitura estão implementadas e testadas:

| # | Tool | Módulo |
|---|---|---|
| 1 | finanpy_health | tools/health.py |
| 5 | finanpy_list_accounts | tools/accounts.py |
| 6 | finanpy_list_categories | tools/categories.py |
| 7 | finanpy_list_subcategories | tools/categories.py |
| 10 | finanpy_list_tags | tools/tags.py |
| 13 | finanpy_list_transactions | tools/transactions.py |
| 2 | finanpy_dashboard_snapshot | tools/reports.py |
| 3 | finanpy_monthly_summary | tools/reports.py |
| 4 | finanpy_yearly_summary | tools/reports.py |
| 16 | finanpy_list_budgets | tools/budgets.py |
| 17 | finanpy_list_goals | tools/goals.py |
| 18 | finanpy_get_monthly_plan | tools/plans.py |

> **Continua em Parte 3/3** — Tools de escrita (create_category, update_category,
> create_tag, update_tag, register_quick_transaction, confirm_pending_transaction,
> add_goal_contribution) + smoke script + deploy scripts