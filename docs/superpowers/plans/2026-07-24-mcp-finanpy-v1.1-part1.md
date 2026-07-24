# MCP FinanPy v1.1 — Plano de Implementação (Parte 1/3)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refatorar o MCP do FinanPy para usar HTTP API + DRF Token (padrão brabus), substituindo o acesso direto ao DB, com 19 tools cobrindo leitura, escrita de transações, categorias, tags e contribuições de metas.

**Architecture:** FastMCP (stdio) → httpx (Bearer DRF Token, loopback 127.0.0.1:8001) → Django REST Framework (/api/v1/). Sanitização de segredos no payload de saída. Deploy via rsync para VPS.

**Tech Stack:** Python 3.12+, mcp[cli]>=1.0, httpx, python-dotenv, pytest, respx. Django 5.2+ DRF no backend.

**Spec:** `docs/superpowers/specs/2026-07-24-mcp-finanpy-v1.1-design.md`

---

## Pré-requisito: Git Tag

- [ ] **Step 0: Tag do estado atual antes do rewrite**

```bash
cd /home/jrmelo/Projetos/finanpy_v2
git tag mcp/v0-direct-db
```

Verificar: `git tag -l 'mcp/v0*'`

---

## Task 1: Patch MonthlyPlanViewSet — filtrar por year/month

**Files:**
- Modify: `api/views.py:704-707` ( MonthlyPlanViewSet.get_queryset)
- Test: `api/tests.py`

- [ ] **Step 1: Write the failing test**

Adicionar em `api/tests.py` (dentro de classe existente de testes de MonthlyPlan, ou criar nova):

```python
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from budgets.models import MonthlyPlan

User = get_user_model()


class MonthlyPlanFilterTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='plan_test', password='x')
        self.client.force_authenticate(user=self.user)
        MonthlyPlan.objects.create(user=self.user, year=2026, month=6)
        MonthlyPlan.objects.create(user=self.user, year=2026, month=7)
        MonthlyPlan.objects.create(user=self.user, year=2025, month=12)

    def test_filter_by_year_and_month(self):
        resp = self.client.get('/api/v1/monthly-plans/?year=2026&month=7')
        self.assertEqual(resp.status_code, 200)
        results = resp.data.get('results', resp.data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['year'], 2026)
        self.assertEqual(results[0]['month'], 7)

    def test_filter_by_year_only(self):
        resp = self.client.get('/api/v1/monthly-plans/?year=2026')
        results = resp.data.get('results', resp.data)
        self.assertEqual(len(results), 2)

    def test_no_filter_returns_all(self):
        resp = self.client.get('/api/v1/monthly-plans/')
        results = resp.data.get('results', resp.data)
        self.assertEqual(len(results), 3)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python manage.py test api.tests.MonthlyPlanFilterTest -v 2`
Expected: FAIL — os 3 planos são retornados em todos os casos porque get_queryset não filtra.

- [ ] **Step 3: Write minimal implementation**

Substituir `MonthlyPlanViewSet.get_queryset` em `api/views.py:704-707`:

```python
    def get_queryset(self):
        qs = MonthlyPlan.objects.filter(
            user=self.request.user
        ).order_by('-year', '-month')

        params = self.request.query_params
        year = params.get('year')
        month = params.get('month')
        if year:
            try:
                qs = qs.filter(year=int(year))
            except ValueError:
                pass
        if month:
            try:
                qs = qs.filter(month=int(month))
            except ValueError:
                pass
        return qs
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python manage.py test api.tests.MonthlyPlanFilterTest -v 2`
Expected: PASS — 3 testes

- [ ] **Step 5: Commit**

```bash
git add api/views.py api/tests.py
git commit -m "feat(api): filter MonthlyPlanViewSet by year and month query params"
```

---

## Task 2: Config — carregar FINANPY_API_BASE_URL e FINANPY_API_TOKEN

**Files:**
- Modify: `mcp/finanpy_mcp/config.py` (rewrite completo)
- Modify: `mcp/.env.example`
- Test: `mcp/tests/test_config.py`

- [ ] **Step 1: Write the failing test**

Criar `mcp/tests/test_config.py`:

```python
import os
from finanpy_mcp.config import Config


def test_config_from_env_success(monkeypatch):
    monkeypatch.setenv('FINANPY_API_BASE_URL', 'http://127.0.0.1:8001/api/v1/')
    monkeypatch.setenv('FINANPY_API_TOKEN', 'a' * 40)
    cfg = Config.from_env()
    assert cfg.base_url == 'http://127.0.0.1:8001/api/v1/'
    assert cfg.token == 'a' * 40
    assert cfg.timeout_seconds == 20.0


def test_config_missing_base_url(monkeypatch):
    monkeypatch.delenv('FINANPY_API_BASE_URL', raising=False)
    monkeypatch.setenv('FINANPY_API_TOKEN', 'a' * 40)
    try:
        Config.from_env()
        assert False, "Should have raised"
    except ValueError as e:
        assert 'FINANPY_API_BASE_URL' in str(e)


def test_config_base_url_without_trailing_slash(monkeypatch):
    monkeypatch.setenv('FINANPY_API_BASE_URL', 'http://127.0.0.1:8001/api/v1')
    monkeypatch.setenv('FINANPY_API_TOKEN', 'a' * 40)
    try:
        Config.from_env()
        assert False, "Should have raised"
    except ValueError as e:
        assert '/api/v1/' in str(e)


def test_config_token_too_short(monkeypatch):
    monkeypatch.setenv('FINANPY_API_BASE_URL', 'http://127.0.0.1:8001/api/v1/')
    monkeypatch.setenv('FINANPY_API_TOKEN', 'short')
    try:
        Config.from_env()
        assert False, "Should have raised"
    except ValueError as e:
        assert 'FINANPY_API_TOKEN' in str(e)


def test_config_custom_timeout(monkeypatch):
    monkeypatch.setenv('FINANPY_API_BASE_URL', 'http://127.0.0.1:8001/api/v1/')
    monkeypatch.setenv('FINANPY_API_TOKEN', 'a' * 40)
    monkeypatch.setenv('FINANPY_API_TIMEOUT_SECONDS', '30')
    cfg = Config.from_env()
    assert cfg.timeout_seconds == 30.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd mcp && .venv/bin/python -m pytest tests/test_config.py -v`
Expected: FAIL — `Config` ainda tem campos `use_sqlite`, `db_path`, etc.

- [ ] **Step 3: Write minimal implementation**

Rewrite de `mcp/finanpy_mcp/config.py`:

```python
"""Configuration loading from environment variables."""
import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    """FinanPy MCP configuration."""

    base_url: str
    token: str
    timeout_seconds: float = 20.0

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        base_url = os.getenv("FINANPY_API_BASE_URL", "").strip().rstrip("/")
        if not base_url:
            raise ValueError(
                "FINANPY_API_BASE_URL é obrigatório "
                "(ex.: http://127.0.0.1:8001/api/v1/)"
            )
        if not base_url.endswith("/api/v1"):
            raise ValueError(
                "FINANPY_API_BASE_URL deve terminar com /api/v1/ "
                f"(recebido: {base_url})"
            )

        token = os.getenv("FINANPY_API_TOKEN", "").strip()
        if len(token) < 20:
            raise ValueError(
                "FINANPY_API_TOKEN é obrigatório e deve ter pelo menos "
                "20 caracteres."
            )

        timeout_str = os.getenv("FINANPY_API_TIMEOUT_SECONDS", "20")
        try:
            timeout_seconds = float(timeout_str)
        except ValueError:
            timeout_seconds = 20.0

        return cls(
            base_url=base_url,
            token=token,
            timeout_seconds=timeout_seconds,
        )


def get_config() -> Config:
    """Get MCP configuration."""
    return Config.from_env()
```

Atualizar `mcp/.env.example`:

```bash
# FinanPy Backend (loopback Docker container)
FINANPY_API_BASE_URL=http://127.0.0.1:8001/api/v1/
FINANPY_API_TOKEN=<cole-aqui-o-token-do-user-hermes>
FINANPY_API_TIMEOUT_SECONDS=20
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd mcp && .venv/bin/python -m pytest tests/test_config.py -v`
Expected: PASS — 5 testes

- [ ] **Step 5: Commit**

```bash
git add mcp/finanpy_mcp/config.py mcp/.env.example mcp/tests/test_config.py
git commit -m "refactor(mcp): config loads API_BASE_URL and TOKEN instead of DB params"
```

---

## Task 3: Sanitization — redação de segredos em payloads

**Files:**
- Create: `mcp/finanpy_mcp/sanitization.py`
- Test: `mcp/tests/test_sanitization.py`

- [ ] **Step 1: Write the failing test**

Criar `mcp/tests/test_sanitization.py`:

```python
from finanpy_mcp.sanitization import sanitize_payload


def test_redacts_token_key():
    payload = {"token": "abc123", "name": "João"}
    result = sanitize_payload(payload)
    assert result["token"] == "***redacted***"
    assert result["name"] == "João"


def test_redacts_authorization():
    payload = {"Authorization": "Bearer xyz", "data": [1, 2]}
    result = sanitize_payload(payload)
    assert result["Authorization"] == "***redacted***"
    assert result["data"] == [1, 2]


def test_redacts_nested():
    payload = {
        "outer": {"api_key": "secret", "normal": "ok"},
        "list": [{"password": "p", "id": 1}],
    }
    result = sanitize_payload(payload)
    assert result["outer"]["api_key"] == "***redacted***"
    assert result["outer"]["normal"] == "ok"
    assert result["list"][0]["password"] == "***redacted***"
    assert result["list"][0]["id"] == 1


def test_redacts_case_insensitive():
    payload = {"API_Key": "secret", "SECRET": "s"}
    result = sanitize_payload(payload)
    assert result["API_Key"] == "***redacted***"
    assert result["SECRET"] == "***redacted***"


def test_preserves_none():
    payload = {"token": None, "name": "x"}
    result = sanitize_payload(payload)
    assert result["token"] is None


def test_handles_plain_string():
    assert sanitize_payload("hello") == "hello"
    assert sanitize_payload(42) == 42
    assert sanitize_payload([]) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd mcp && .venv/bin/python -m pytest tests/test_sanitization.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'finanpy_mcp.sanitization'`

- [ ] **Step 3: Write minimal implementation**

Criar `mcp/finanpy_mcp/sanitization.py`:

```python
"""Sanitization of secrets in payloads returned to the agent."""
import re
from typing import Any

_SECRET_KEY_RE = re.compile(
    r"(token|secret|password|authorization|api[_-]?key|bearer|cookie|session)",
    re.I,
)


def _mask_value(key: str, value: Any) -> Any:
    if value is None:
        return None
    if _SECRET_KEY_RE.search(key):
        return "***redacted***"
    return value


def sanitize_payload(value: Any, *, key: str = "") -> Any:
    """Recursively redact secret-like keys from a payload."""
    masked = _mask_value(key, value) if key else value
    if masked != value:
        return masked

    if isinstance(value, dict):
        return {str(k): sanitize_payload(v, key=str(k)) for k, v in value.items()}
    if isinstance(value, list):
        return [sanitize_payload(item, key=key) for item in value]
    return value
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd mcp && .venv/bin/python -m pytest tests/test_sanitization.py -v`
Expected: PASS — 6 testes

- [ ] **Step 5: Commit**

```bash
git add mcp/finanpy_mcp/sanitization.py mcp/tests/test_sanitization.py
git commit -m "feat(mcp): add sanitization module for redacting secrets in payloads"
```

---

## Task 4: HTTP Client — wrapper httpx com Bearer, timeout e erros

**Files:**
- Create: `mcp/finanpy_mcp/http_client.py`
- Test: `mcp/tests/test_http_client.py`

- [ ] **Step 1: Write the failing test**

Criar `mcp/tests/test_http_client.py`:

```python
import httpx
import pytest
from finanpy_mcp.http_client import FinanPyClient, FinanPyMCPError


def _mock_transport(status_code, json_body):
    def handler(request):
        return httpx.Response(status_code, json=json_body)
    return httpx.MockTransport(handler)


def _client(transport):
    return FinanPyClient(
        base_url="http://127.0.0.1:8001/api/v1/",
        token="t" * 40,
        timeout=10.0,
        transport=transport,
    )


def test_request_sends_bearer_token():
    captured = {}

    def handler(request):
        captured["auth"] = request.headers.get("authorization")
        captured["accept"] = request.headers.get("accept")
        return httpx.Response(200, json={"ok": True})

    client = _client(httpx.MockTransport(handler))
    result = client.request("GET", "accounts/")
    assert result == {"ok": True}
    assert captured["auth"] == f"Bearer t{'t' * 39}"
    assert captured["accept"] == "application/json"


def test_request_400_raises_error():
    client = _client(_mock_transport(400, {"detail": "Bad request"}))
    with pytest.raises(FinanPyMCPError, match="rejeitou"):
        client.request("GET", "accounts/")


def test_request_401_raises_error():
    client = _client(_mock_transport(401, {"detail": "Invalid token"}))
    with pytest.raises(FinanPyMCPError, match="Token.*inválido"):
        client.request("GET", "accounts/")


def test_request_404_raises_error():
    client = _client(_mock_transport(404, {"detail": "Not found"}))
    with pytest.raises(FinanPyMCPError, match="não encontrado"):
        client.request("GET", "accounts/42/")


def test_request_500_raises_error():
    client = _client(_mock_transport(500, {"error": "Internal"}))
    with pytest.raises(FinanPyMCPError, match="HTTP 500"):
        client.request("GET", "accounts/")


def test_request_timeout():
    def handler(request):
        raise httpx.TimeoutException("timed out")
    client = _client(httpx.MockTransport(handler))
    with pytest.raises(FinanPyMCPError, match="Tempo esgotado"):
        client.request("GET", "accounts/")


def test_request_connection_error():
    def handler(request):
        raise httpx.ConnectError("conn refused")
    client = _client(httpx.MockTransport(handler))
    with pytest.raises(FinanPyMCPError, match="Falha de comunicação"):
        client.request("GET", "accounts/")


def test_request_non_json():
    def handler(request):
        return httpx.Response(200, content=b"not json", headers={"content-type": "text/plain"})
    client = _client(httpx.MockTransport(handler))
    with pytest.raises(FinanPyMCPError, match="não-JSON"):
        client.request("GET", "accounts/")


def test_post_sends_json_body():
    captured = {}

    def handler(request):
        captured["body"] = request.read()
        captured["content_type"] = request.headers.get("content-type")
        return httpx.Response(201, json={"id": 99})

    client = _client(httpx.MockTransport(handler))
    result = client.request("POST", "transactions/quick/", json={"amount": "50.00"})
    assert result == {"id": 99}
    assert b"50.00" in captured["body"]
    assert "application/json" in captured["content_type"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd mcp && .venv/bin/python -m pytest tests/test_http_client.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'finanpy_mcp.http_client'`

- [ ] **Step 3: Write minimal implementation**

Criar `mcp/finanpy_mcp/http_client.py`:

```python
"""HTTP client for FinanPy DRF API."""
import httpx

from .sanitization import sanitize_payload


class FinanPyMCPError(Exception):
    """Safe error for FinanPy API failures."""


class FinanPyClient:
    """Thin httpx wrapper with Bearer auth, timeout and error normalization."""

    def __init__(
        self,
        base_url: str,
        token: str,
        timeout: float = 20.0,
        transport: httpx.BaseTransport | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self._timeout = timeout
        self._transport = transport

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict | None = None,
        json: dict | None = None,
    ) -> dict:
        """Make an HTTP request and return parsed JSON. Raises FinanPyMCPError on failure."""
        url = f"{self.base_url}/{path.lstrip('/')}"

        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.token}",
            "User-Agent": "Hermes/FinanPyMCP 1.1",
        }
        if json is not None:
            headers["Content-Type"] = "application/json"

        try:
            with httpx.Client(
                timeout=self._timeout,
                headers=headers,
                follow_redirects=False,
                transport=self._transport,
            ) as client:
                response = client.request(method, url, params=params, json=json)
        except httpx.TimeoutException:
            raise FinanPyMCPError("Tempo esgotado ao consultar a API do FinanPy.")
        except httpx.RequestError:
            raise FinanPyMCPError("Falha de comunicação ao consultar a API do FinanPy.")

        try:
            payload = response.json()
        except Exception:
            raise FinanPyMCPError("Resposta não-JSON recebida da API do FinanPy.")

        if response.status_code == 401:
            raise FinanPyMCPError("Token FinanPy inválido ou expirado.")
        if response.status_code == 404:
            raise FinanPyMCPError("Recurso FinanPy não encontrado.")
        if response.status_code >= 400:
            detail = ""
            if isinstance(payload, dict):
                detail = str(payload.get("detail") or payload)
            detail = sanitize_payload({"d": detail})["d"]
            if response.status_code == 400:
                raise FinanPyMCPError(f"FinanPy rejeitou a operação: {detail}")
            raise FinanPyMCPError(
                f"FinanPy API erro HTTP {response.status_code}: {detail}"
            )

        return payload
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd mcp && .venv/bin/python -m pytest tests/test_http_client.py -v`
Expected: PASS — 9 testes

- [ ] **Step 5: Commit**

```bash
git add mcp/finanpy_mcp/http_client.py mcp/tests/test_http_client.py
git commit -m "feat(mcp): add httpx-based HTTP client with Bearer auth and error normalization"
```

---

## Task 5: Atualizar pyproject.toml e deletar client.py antigo

**Files:**
- Modify: `mcp/pyproject.toml` (remover psycopg2, adicionar httpx + respx)
- Delete: `mcp/finanpy_mcp/client.py`
- Delete: `mcp/finanpy_mcp/tools/__pycache__/client*.pyc`

- [ ] **Step 1: Atualizar pyproject.toml**

Substituir conteúdo de `mcp/pyproject.toml`:

```toml
[project]
name = "finanpy-mcp"
version = "1.1.0"
description = "MCP Server for FinanPy (Hermes agent integration via DRF API)"
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

[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"
```

- [ ] **Step 2: Reinstalar deps na venv**

Run: `cd mcp && .venv/bin/pip install -e '.[dev]' -q`

- [ ] **Step 3: Deletar client.py antigo**

```bash
rm mcp/finanpy_mcp/client.py
rm -rf mcp/finanpy_mcp/__pycache__/client*.pyc
rm -rf mcp/finanpy_mcp/tools/__pycache__/client*.pyc
```

- [ ] **Step 4: Verificar que nada importa client.py ainda**

Run: `grep -rn 'from.*client import\|import.*client' mcp/finanpy_mcp/ --include='*.py' | grep -v __pycache__`
Expected: output vazio (sem importações órfãs)

- [ ] **Step 5: Commit**

```bash
git add mcp/pyproject.toml
git rm mcp/finanpy_mcp/client.py
git commit -m "refactor(mcp): remove psycopg2 and direct-DB client in favor of httpx + DRF API"
```

---

## Task 6: Server FastMCP — entry point + registro de tools (stub vazio)

**Files:**
- Modify: `mcp/finanpy_mcp/server.py` (rewrite completo)
- Modify: `mcp/run_mcp.py`

- [ ] **Step 1: Write minimal implementation**

Rewrite de `mcp/finanpy_mcp/server.py`:

```python
"""MCP FinanPy Server."""
import logging

from mcp.server.fastmcp import FastMCP

from .config import get_config
from .http_client import FinanPyClient
from .tools.health import register_health_tools
from .tools.accounts import register_account_tools
from .tools.categories import register_category_tools
from .tools.tags import register_tag_tools
from .tools.transactions import register_transaction_tools
from .tools.reports import register_report_tools
from .tools.budgets import register_budget_tools
from .tools.goals import register_goal_tools
from .tools.plans import register_plan_tools

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

mcp = FastMCP("finanpy")


def _get_client() -> FinanPyClient:
    cfg = get_config()
    return FinanPyClient(
        base_url=cfg.base_url,
        token=cfg.token,
        timeout=cfg.timeout_seconds,
    )


def _register_all():
    client = _get_client()
    register_health_tools(mcp, client)
    register_account_tools(mcp, client)
    register_category_tools(mcp, client)
    register_tag_tools(mcp, client)
    register_transaction_tools(mcp, client)
    register_report_tools(mcp, client)
    register_budget_tools(mcp, client)
    register_goal_tools(mcp, client)
    register_plan_tools(mcp, client)


_register_all()


def main():
    """Run the MCP server (stdio transport)."""
    mcp.run()


if __name__ == "__main__":
    main()
```

Rewrite de `mcp/run_mcp.py`:

```python
#!/usr/bin/env python3
"""MCP FinanPy Server entry point."""
from finanpy_mcp.server import main

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Criar stubs de cada tool module para import não falhar**

Criar `mcp/finanpy_mcp/tools/health.py`:

```python
"""Health-related MCP tools."""


def register_health_tools(mcp, client):
    """Register health tools. Placeholder — filled in Task 7."""
    pass
```

Repetir a mesma estrutura para `accounts.py`, `categories.py`, `tags.py`, `transactions.py`, `reports.py`, `budgets.py`, `goals.py`, `plans.py` substituindo o nome da função `register_health_tools` pelo correspondente:

| Arquivo | Função |
|---|---|
| `accounts.py` | `register_account_tools` |
| `categories.py` | `register_category_tools` |
| `tags.py` | `register_tag_tools` |
| `transactions.py` | `register_transaction_tools` |
| `reports.py` | `register_report_tools` |
| `budgets.py` | `register_budget_tools` |
| `goals.py` | `register_goal_tools` |
| `plans.py` | `register_plan_tools` |

Cada arquivo stub:

```python
"""<Domain>-related MCP tools."""


def register_<domain>_tools(mcp, client):
    """Register <domain> tools. Placeholder — filled in later tasks."""
    pass
```

- [ ] **Step 3: Verificar que o server inicia sem erro**

Run: `cd mcp && .venv/bin/python -c "from finanpy_mcp.server import mcp; print('OK', mcp.name)"`
Expected: `OK finanpy`

- [ ] **Step 4: Commit**

```bash
git add mcp/finanpy_mcp/server.py mcp/run_mcp.py mcp/finanpy_mcp/tools/
git commit -m "refactor(mcp): FastMCP server with tool registration stubs"
```

---

## Fim da Parte 1

---

> **Continua em Parte 2/3** — Tools de leitura (health, list_accounts, list_categories, list_tags, list_transactions, list_budgets, list_goals, get_monthly_plan, dashboard_snapshot, monthly_summary, yearly_summary)
>
> **Parte 3/3** — Tools de escrita (create/update category, create/update tag, register_quick_transaction, confirm_pending, add_goal_contribution) + deploy scripts