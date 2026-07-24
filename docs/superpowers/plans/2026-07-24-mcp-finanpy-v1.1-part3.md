# MCP FinanPy v1.1 — Plano de Implementação (Parte 3/3)

> Continuação de Parte 2/3. Ler Parte 1 e 2 primeiro.

**Goal desta parte:** Implementar 7 tools de escrita (create_category, update_category, create_tag, update_tag, register_quick_transaction, confirm_pending_transaction, add_goal_contribution) + smoke script + deploy scripts.

---

## Task 13: Create + Update Category tools

**Files:**
- Modify: `mcp/finanpy_mcp/tools/categories.py` (adicionar 2 funções + 2 registrations)
- Test: `mcp/tests/test_tools_categories_write.py`

- [ ] **Step 1: Write the failing test**

Criar `mcp/tests/test_tools_categories_write.py`:

```python
import json
import pytest
import respx
from finanpy_mcp.tools.categories import create_category, update_category
from finanpy_mcp.http_client import FinanPyClient


@pytest.fixture
def client():
    return FinanPyClient(
        base_url="http://test/api/v1/",
        token="t" * 40,
        timeout=5.0,
    )


@respx.mock
def test_create_category_minimal(client):
    route = respx.post("http://test/api/v1/categories/")
    route.respond(201, json={"id": 5, "name": "Mercado", "category_type": "EXPENSE"})
    r = create_category(client, name="Mercado", category_type="EXPENSE")
    assert r["ok"] is True
    assert r["payload"]["id"] == 5
    body = json.loads(route.calls.last.request.content)
    assert body["name"] == "Mercado"
    assert body["category_type"] == "EXPENSE"
    assert body["color"] == "#10B981"
    assert body["icon"] == "💰"
    assert body["is_active"] is True
    assert "parent" not in body or body["parent"] is None


@respx.mock
def test_create_category_with_parent(client):
    route = respx.post("http://test/api/v1/categories/")
    route.respond(201, json={"id": 6, "name": "Padaria", "category_type": "EXPENSE"})
    r = create_category(client, name="Padaria", category_type="EXPENSE", parent=5, color="#EF4444", icon="🍞")
    assert r["ok"] is True
    body = json.loads(route.calls.last.request.content)
    assert body["parent"] == 5
    assert body["color"] == "#EF4444"
    assert body["icon"] == "🍞"


@respx.mock
def test_create_category_invalid_type(client):
    r = create_category(client, name="X", category_type="INVALIDO")
    assert r["ok"] is False
    assert "category_type" in r["error"]


@respx.mock
def test_create_category_invalid_color(client):
    r = create_category(client, name="X", category_type="EXPENSE", color="red")
    assert r["ok"] is False
    assert "color" in r["error"]


@respx.mock
def test_create_category_name_truncated(client):
    route = respx.post("http://test/api/v1/categories/")
    route.respond(201, json={"id": 7})
    long_name = "x" * 100
    r = create_category(client, name=long_name, category_type="EXPENSE")
    assert r["ok"] is True
    body = json.loads(route.calls.last.request.content)
    assert len(body["name"]) == 50


@respx.mock
def test_create_category_api_error(client):
    respx.post("http://test/api/v1/categories/").respond(400, json={"name": ["This field is required."]})
    r = create_category(client, name="X", category_type="EXPENSE")
    assert r["ok"] is False
    assert "rejeitou" in r["error"]


@respx.mock
def test_update_category_partial(client):
    route = respx.patch("http://test/api/v1/categories/5/")
    route.respond(200, json={"id": 5, "name": "Alimentação Atualizada"})
    r = update_category(client, id=5, name="Alimentação Atualizada")
    assert r["ok"] is True
    body = json.loads(route.calls.last.request.content)
    assert body == {"name": "Alimentação Atualizada"}


@respx.mock
def test_update_category_deactivate(client):
    route = respx.patch("http://test/api/v1/categories/3/")
    route.respond(200, json={"id": 3, "is_active": False})
    r = update_category(client, id=3, is_active=False)
    assert r["ok"] is True
    body = json.loads(route.calls.last.request.content)
    assert body == {"is_active": False}


@respx.mock
def test_update_category_no_fields(client):
    r = update_category(client, id=5)
    assert r["ok"] is False
    assert "nada" in r["error"].lower() or "no field" in r["error"].lower()


@respx.mock
def test_update_category_api_error(client):
    respx.patch("http://test/api/v1/categories/999/").respond(404, json={"detail": "Not found"})
    r = update_category(client, id=999, name="X")
    assert r["ok"] is False
    assert "não encontrado" in r["error"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd mcp && .venv/bin/python -m pytest tests/test_tools_categories_write.py -v`
Expected: FAIL — `create_category` e `update_category` não existem

- [ ] **Step 3: Write minimal implementation**

Adicionar em `mcp/finanpy_mcp/tools/categories.py` (após `list_subcategories`, antes de `register_category_tools`):

```python
import re

from ..helpers import _result, _safe_call, _filter_params, _clean_text


_CATEGORY_TYPE_CHOICES = {"INCOME", "EXPENSE"}
_COLOR_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")


def create_category(
    client,
    name,
    category_type,
    color="#10B981",
    icon="💰",
    parent=None,
    is_active=True,
) -> dict:
    """Create a new category or subcategory."""
    name = _clean_text(name, max_len=50)
    if not name:
        return {"ok": False, "error": "name é obrigatório."}
    if category_type not in _CATEGORY_TYPE_CHOICES:
        return {"ok": False, "error": f"category_type deve ser um de {sorted(_CATEGORY_TYPE_CHOICES)}."}
    if not _COLOR_RE.match(color):
        return {"ok": False, "error": "color deve ser um hex válido (ex.: #10B981)."}
    icon = _clean_text(icon, max_len=10)

    body = {
        "name": name,
        "category_type": category_type,
        "color": color,
        "icon": icon,
        "is_active": is_active,
    }
    if parent is not None:
        body["parent"] = parent

    return _safe_call(lambda: _result(
        "categories/create",
        client.request("POST", "categories/", json=body),
        body,
    ))


def update_category(
    client,
    id,
    name=None,
    category_type=None,
    color=None,
    icon=None,
    parent=None,
    is_active=None,
) -> dict:
    """Update fields of an existing category (partial update)."""
    body = {}
    if name is not None:
        name = _clean_text(name, max_len=50)
        if not name:
            return {"ok": False, "error": "name não pode ser vazio."}
        body["name"] = name
    if category_type is not None:
        if category_type not in _CATEGORY_TYPE_CHOICES:
            return {"ok": False, "error": f"category_type deve ser um de {sorted(_CATEGORY_TYPE_CHOICES)}."}
        body["category_type"] = category_type
    if color is not None:
        if not _COLOR_RE.match(color):
            return {"ok": False, "error": "color deve ser um hex válido (ex.: #10B981)."}
        body["color"] = color
    if icon is not None:
        body["icon"] = _clean_text(icon, max_len=10)
    if parent is not None:
        body["parent"] = parent
    if is_active is not None:
        body["is_active"] = is_active

    if not body:
        return {"ok": False, "error": "Nada para atualizar — forneça ao menos um campo."}

    return _safe_call(lambda: _result(
        "categories/update",
        client.request("PATCH", f"categories/{id}/", json=body),
        {"id": id, **body},
    ))
```

Adicionar dentro de `register_category_tools` (após `finanpy_list_subcategories`):

```python
    @mcp.tool()
    def finanpy_create_category(
        name: str,
        category_type: str,
        color: str = "#10B981",
        icon: str = "💰",
        parent: int | None = None,
        is_active: bool = True,
    ) -> dict:
        """Cria uma nova categoria ou subcategoria.

        Args:
            name: Nome da categoria (máx 50 caracteres)
            category_type: "INCOME" ou "EXPENSE"
            color: Hex color (ex.: "#10B981"). Default: verde
            icon: Emoji (ex.: "🍔"). Default: 💰
            parent: ID da categoria pai (para subcategoria). Opcional.
            is_active: True (default) para ativa

        Returns:
            {ok, endpoint, params, payload} — payload tem {id, name, ...}
        """
        return create_category(
            client, name=name, category_type=category_type,
            color=color, icon=icon, parent=parent, is_active=is_active,
        )

    @mcp.tool()
    def finanpy_update_category(
        id: int,
        name: str | None = None,
        category_type: str | None = None,
        color: str | None = None,
        icon: str | None = None,
        parent: int | None = None,
        is_active: bool | None = None,
    ) -> dict:
        """Atualiza campos de uma categoria existente (partial update).

        Use is_active=False para desativar (soft-delete) em vez de deletar.

        Args:
            id: ID da categoria
            name: Novo nome (opcional)
            category_type: "INCOME" ou "EXPENSE" (opcional)
            color: Novo hex color (opcional)
            icon: Novo emoji (opcional)
            parent: Novo ID pai (opcional)
            is_active: True/False para ativar/desativar (opcional)

        Returns:
            {ok, endpoint, params, payload} — payload tem a categoria atualizada
        """
        return update_category(
            client, id=id, name=name, category_type=category_type,
            color=color, icon=icon, parent=parent, is_active=is_active,
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd mcp && .venv/bin/python -m pytest tests/test_tools_categories_write.py -v`
Expected: PASS — 11 testes

- [ ] **Step 5: Commit**

```bash
git add mcp/finanpy_mcp/tools/categories.py mcp/tests/test_tools_categories_write.py
git commit -m "feat(mcp): add create_category and update_category tools"
```

---

## Task 14: Create + Update Tag tools

**Files:**
- Modify: `mcp/finanpy_mcp/tools/tags.py`
- Test: `mcp/tests/test_tools_tags_write.py`

- [ ] **Step 1: Write the failing test**

Criar `mcp/tests/test_tools_tags_write.py`:

```python
import json
import pytest
import respx
from finanpy_mcp.tools.tags import create_tag, update_tag
from finanpy_mcp.http_client import FinanPyClient


@pytest.fixture
def client():
    return FinanPyClient(
        base_url="http://test/api/v1/",
        token="t" * 40,
        timeout=5.0,
    )


@respx.mock
def test_create_tag_normalizes_lower(client):
    route = respx.post("http://test/api/v1/tags/")
    route.respond(201, json={"id": 1, "name": "recorrente"})
    r = create_tag(client, name="  RECORRENTE  ")
    assert r["ok"] is True
    body = json.loads(route.calls.last.request.content)
    assert body == {"name": "recorrente"}


@respx.mock
def test_create_tag_empty_returns_error(client):
    r = create_tag(client, name="   ")
    assert r["ok"] is False
    assert "name" in r["error"].lower() or "vazio" in r["error"].lower()


@respx.mock
def test_create_tag_truncates(client):
    route = respx.post("http://test/api/v1/tags/")
    route.respond(201, json={"id": 2, "name": "x" * 50})
    r = create_tag(client, name="x" * 100)
    assert r["ok"] is True
    body = json.loads(route.calls.last.request.content)
    assert len(body["name"]) == 50


@respx.mock
def test_create_tag_api_duplicate(client):
    respx.post("http://test/api/v1/tags/").respond(400, json={"name": ["Tag com este nome já existe."]})
    r = create_tag(client, name="recorrente")
    assert r["ok"] is False
    assert "rejeitou" in r["error"]


@respx.mock
def test_update_tag(client):
    route = respx.patch("http://test/api/v1/tags/3/")
    route.respond(200, json={"id": 3, "name": "novo-nome"})
    r = update_tag(client, id=3, name="  NOVO-NOME  ")
    assert r["ok"] is True
    body = json.loads(route.calls.last.request.content)
    assert body == {"name": "novo-nome"}


@respx.mock
def test_update_tag_empty_name(client):
    r = update_tag(client, id=3, name="")
    assert r["ok"] is False
    assert "vazio" in r["error"].lower()


@respx.mock
def test_update_tag_api_error(client):
    respx.patch("http://test/api/v1/tags/999/").respond(404, json={"detail": "Not found"})
    r = update_tag(client, id=999, name="x")
    assert r["ok"] is False
    assert "não encontrado" in r["error"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd mcp && .venv/bin/python -m pytest tests/test_tools_tags_write.py -v`
Expected: FAIL — funções não existem

- [ ] **Step 3: Write minimal implementation**

Adicionar em `mcp/finanpy_mcp/tools/tags.py` (após `list_tags`, antes de `register_tag_tools`):

```python
from ..helpers import _result, _safe_call, _clean_text


def create_tag(client, name) -> dict:
    """Create a new tag. Name is normalized to lowercase/strip."""
    name = _clean_text(name, max_len=50).lower()
    if not name:
        return {"ok": False, "error": "name não pode ser vazio."}
    body = {"name": name}
    return _safe_call(lambda: _result(
        "tags/create",
        client.request("POST", "tags/", json=body),
        body,
    ))


def update_tag(client, id, name) -> dict:
    """Update a tag's name. Name is normalized to lowercase/strip."""
    name = _clean_text(name, max_len=50).lower()
    if not name:
        return {"ok": False, "error": "name não pode ser vazio."}
    body = {"name": name}
    return _safe_call(lambda: _result(
        "tags/update",
        client.request("PATCH", f"tags/{id}/", json=body),
        {"id": id, **body},
    ))
```

Adicionar dentro de `register_tag_tools` (após `finanpy_list_tags`):

```python
    @mcp.tool()
    def finanpy_create_tag(name: str) -> dict:
        """Cria uma nova tag. O nome é normalizado (lowercase, sem espaços extras).

        Args:
            name: Nome da tag (máx 50 caracteres, normalizado para lowercase)

        Returns:
            {ok, endpoint, params, payload} — payload tem {id, name, created_at}
        """
        return create_tag(client, name=name)

    @mcp.tool()
    def finanpy_update_tag(id: int, name: str) -> dict:
        """Atualiza o nome de uma tag existente.

        Args:
            id: ID da tag
            name: Novo nome (normalizado para lowercase, máx 50 chars)

        Returns:
            {ok, endpoint, params, payload} — payload tem a tag atualizada
        """
        return update_tag(client, id=id, name=name)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd mcp && .venv/bin/python -m pytest tests/test_tools_tags_write.py -v`
Expected: PASS — 7 testes

- [ ] **Step 5: Commit**

```bash
git add mcp/finanpy_mcp/tools/tags.py mcp/tests/test_tools_tags_write.py
git commit -m "feat(mcp): add create_tag and update_tag tools with name normalization"
```

---

## Task 15: Register Quick Transaction tool

**Files:**
- Modify: `mcp/finanpy_mcp/tools/transactions.py` (adicionar função + registration)
- Test: `mcp/tests/test_tools_transactions_quick.py`

- [ ] **Step 1: Write the failing test**

Criar `mcp/tests/test_tools_transactions_quick.py`:

```python
import json
import re
import pytest
import respx
from finanpy_mcp.tools.transactions import register_quick_transaction
from finanpy_mcp.http_client import FinanPyClient


@pytest.fixture
def client():
    return FinanPyClient(
        base_url="http://test/api/v1/",
        token="t" * 40,
        timeout=5.0,
    )


@respx.mock
def test_quick_transaction_generates_client_id(client):
    route = respx.post("http://test/api/v1/transactions/quick/")
    route.respond(201, json={"id": 99, "amount": "50.00"})
    r = register_quick_transaction(
        client, amount="50.00", transaction_type="EXPENSE",
        account=1, category=2,
    )
    assert r["ok"] is True
    body = json.loads(route.calls.last.request.content)
    assert "client_id" in body
    assert body["client_id"].startswith("hermes-")
    assert len(body["client_id"]) > 10
    assert body["amount"] == "50.00"
    assert body["transaction_type"] == "EXPENSE"
    assert body["account"] == 1
    assert body["category"] == 2


@respx.mock
def test_quick_transaction_with_explicit_client_id(client):
    route = respx.post("http://test/api/v1/transactions/quick/")
    route.respond(201, json={"id": 100})
    r = register_quick_transaction(
        client, amount="10.00", transaction_type="INCOME",
        account=1, category=3, client_id="my-custom-id",
    )
    assert r["ok"] is True
    body = json.loads(route.calls.last.request.content)
    assert body["client_id"] == "my-custom-id"


@respx.mock
def test_quick_transaction_with_description_and_date(client):
    route = respx.post("http://test/api/v1/transactions/quick/")
    route.respond(201, json={"id": 101})
    r = register_quick_transaction(
        client, amount="25.50", transaction_type="EXPENSE",
        account=1, category=2,
        description="Almoço", transaction_date="2026-07-24",
        notes="pago em dinheiro",
    )
    assert r["ok"] is True
    body = json.loads(route.calls.last.request.content)
    assert body["description"] == "Almoço"
    assert body["transaction_date"] == "2026-07-24"
    assert body["notes"] == "pago em dinheiro"
    assert "client_id" in body  # still auto-generated


@respx.mock
def test_quick_transaction_invalid_type(client):
    r = register_quick_transaction(
        client, amount="10.00", transaction_type="INVALID",
        account=1, category=2,
    )
    assert r["ok"] is False
    assert "transaction_type" in r["error"]


@respx.mock
def test_quick_transaction_empty_amount(client):
    r = register_quick_transaction(
        client, amount="", transaction_type="EXPENSE",
        account=1, category=2,
    )
    assert r["ok"] is False
    assert "amount" in r["error"].lower()


@respx.mock
def test_quick_transaction_api_error(client):
    respx.post("http://test/api/v1/transactions/quick/").respond(
        400, json={"amount": ["A valid number is required."]}
    )
    r = register_quick_transaction(
        client, amount="abc", transaction_type="EXPENSE",
        account=1, category=2,
    )
    assert r["ok"] is False
    assert "rejeitou" in r["error"]


@respx.mock
def test_quick_transaction_idempotent_response(client):
    route = respx.post("http://test/api/v1/transactions/quick/")
    route.respond(200, json={"id": 99, "amount": "50.00"})
    r = register_quick_transaction(
        client, amount="50.00", transaction_type="EXPENSE",
        account=1, category=2, client_id="dup-123",
    )
    assert r["ok"] is True
    assert r["payload"]["id"] == 99
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd mcp && .venv/bin/python -m pytest tests/test_tools_transactions_quick.py -v`
Expected: FAIL — `register_quick_transaction` não existe

- [ ] **Step 3: Write minimal implementation**

Adicionar em `mcp/finanpy_mcp/tools/transactions.py` (após `list_transactions`):

```python
import uuid

from ..helpers import _result, _safe_call, _filter_params, _safe_int


_TX_TYPE_CHOICES = {"INCOME", "EXPENSE"}


def register_quick_transaction(
    client,
    amount,
    transaction_type,
    account,
    category,
    description=None,
    transaction_date=None,
    notes=None,
    client_id=None,
) -> dict:
    """Register a quick transaction (expense or income) via /transactions/quick/."""
    if transaction_type not in _TX_TYPE_CHOICES:
        return {"ok": False, "error": f"transaction_type deve ser um de {sorted(_TX_TYPE_CHOICES)}."}
    amount_str = str(amount or "").strip()
    if not amount_str:
        return {"ok": False, "error": "amount é obrigatório."}

    if client_id is None:
        client_id = f"hermes-{uuid.uuid4().hex[:8]}"

    body = {
        "amount": amount_str,
        "transaction_type": transaction_type,
        "account": account,
        "category": category,
        "client_id": client_id,
    }
    if description is not None:
        body["description"] = description
    if transaction_date is not None:
        body["transaction_date"] = transaction_date
    if notes is not None:
        body["notes"] = notes

    return _safe_call(lambda: _result(
        "transactions/quick",
        client.request("POST", "transactions/quick/", json=body),
        body,
    ))
```

Adicionar dentro de `register_transaction_tools` (após `finanpy_list_transactions`):

```python
    @mcp.tool()
    def finanpy_register_quick_transaction(
        amount: str,
        transaction_type: str,
        account: int,
        category: int,
        description: str | None = None,
        transaction_date: str | None = None,
        notes: str | None = None,
        client_id: str | None = None,
    ) -> dict:
        """Registra uma transação rápida (despesa ou receita).

        Gera um client_id automaticamente para idempotência (24h) se não fornecido.

        Args:
            amount: Valor como string (ex.: "50.00")
            transaction_type: "EXPENSE" ou "INCOME"
            account: ID da conta
            category: ID da categoria
            description: Descrição (opcional, default = nome da categoria)
            transaction_date: Data no formato YYYY-MM-DD (opcional, default = hoje)
            notes: Notas adicionais (opcional)
            client_id: ID idempotente (opcional, gerado automaticamente se omitido)

        Returns:
            {ok, endpoint, params, payload} — payload tem {id, amount, ...}
        """
        return register_quick_transaction(
            client, amount=amount, transaction_type=transaction_type,
            account=account, category=category,
            description=description, transaction_date=transaction_date,
            notes=notes, client_id=client_id,
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd mcp && .venv/bin/python -m pytest tests/test_tools_transactions_quick.py -v`
Expected: PASS — 7 testes

- [ ] **Step 5: Commit**

```bash
git add mcp/finanpy_mcp/tools/transactions.py mcp/tests/test_tools_transactions_quick.py
git commit -m "feat(mcp): add register_quick_transaction tool with auto client_id"
```

---

## Task 16: Confirm Pending Transaction tool

**Files:**
- Modify: `mcp/finanpy_mcp/tools/transactions.py` (adicionar função + registration)
- Test: `mcp/tests/test_tools_transactions_confirm.py`

- [ ] **Step 1: Write the failing test**

Criar `mcp/tests/test_tools_transactions_confirm.py`:

```python
import pytest
import respx
from finanpy_mcp.tools.transactions import confirm_pending_transaction
from finanpy_mcp.http_client import FinanPyClient


@pytest.fixture
def client():
    return FinanPyClient(
        base_url="http://test/api/v1/",
        token="t" * 40,
        timeout=5.0,
    )


@respx.mock
def test_confirm_pending_success(client):
    respx.post("http://test/api/v1/transactions/42/confirm/").respond(
        200, json={"id": 42, "status": "CONFIRMED"}
    )
    r = confirm_pending_transaction(client, id=42)
    assert r["ok"] is True
    assert r["params"] == {"id": 42}
    assert r["payload"]["status"] == "CONFIRMED"


@respx.mock
def test_confirm_pending_already_confirmed(client):
    respx.post("http://test/api/v1/transactions/42/confirm/").respond(
        400, json={"detail": "Apenas transações pendentes podem ser efetivadas."}
    )
    r = confirm_pending_transaction(client, id=42)
    assert r["ok"] is False
    assert "rejeitou" in r["error"]


@respx.mock
def test_confirm_pending_not_found(client):
    respx.post("http://test/api/v1/transactions/999/confirm/").respond(
        404, json={"detail": "Not found"}
    )
    r = confirm_pending_transaction(client, id=999)
    assert r["ok"] is False
    assert "não encontrado" in r["error"]


@respx.mock
def test_confirm_pending_server_error(client):
    respx.post("http://test/api/v1/transactions/1/confirm/").respond(500, json={"error": "boom"})
    r = confirm_pending_transaction(client, id=1)
    assert r["ok"] is False
    assert "HTTP 500" in r["error"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd mcp && .venv/bin/python -m pytest tests/test_tools_transactions_confirm.py -v`
Expected: FAIL — função não existe

- [ ] **Step 3: Write minimal implementation**

Adicionar em `mcp/finanpy_mcp/tools/transactions.py` (após `register_quick_transaction`):

```python
def confirm_pending_transaction(client, id) -> dict:
    """Confirm a pending transaction."""
    return _safe_call(lambda: _result(
        "transactions/confirm",
        client.request("POST", f"transactions/{id}/confirm/"),
        {"id": id},
    ))
```

Adicionar dentro de `register_transaction_tools` (após `finanpy_register_quick_transaction`):

```python
    @mcp.tool()
    def finanpy_confirm_pending_transaction(id: int) -> dict:
        """Efetiva (confirma) uma transação pendente.

        Args:
            id: ID da transação pendente

        Returns:
            {ok, endpoint, params, payload} — payload tem {id, status: "CONFIRMED", ...}

        Erros comuns:
            - 400: transação não está pendente
            - 404: transação não encontrada
        """
        return confirm_pending_transaction(client, id=id)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd mcp && .venv/bin/python -m pytest tests/test_tools_transactions_confirm.py -v`
Expected: PASS — 4 testes

- [ ] **Step 5: Commit**

```bash
git add mcp/finanpy_mcp/tools/transactions.py mcp/tests/test_tools_transactions_confirm.py
git commit -m "feat(mcp): add confirm_pending_transaction tool"
```

---

## Task 17: Add Goal Contribution tool

**Files:**
- Modify: `mcp/finanpy_mcp/tools/goals.py` (adicionar função + registration)
- Test: `mcp/tests/test_tools_goals_contribution.py`

- [ ] **Step 1: Write the failing test**

Criar `mcp/tests/test_tools_goals_contribution.py`:

```python
import json
import pytest
import respx
from finanpy_mcp.tools.goals import add_goal_contribution
from finanpy_mcp.http_client import FinanPyClient


@pytest.fixture
def client():
    return FinanPyClient(
        base_url="http://test/api/v1/",
        token="t" * 40,
        timeout=5.0,
    )


@respx.mock
def test_add_contribution_with_date(client):
    route = respx.post("http://test/api/v1/goal-contributions/")
    route.respond(201, json={"id": 50, "goal": 3, "amount": "100.00", "date": "2026-07-24"})
    r = add_goal_contribution(client, goal_id=3, amount="100.00", date="2026-07-24")
    assert r["ok"] is True
    body = json.loads(route.calls.last.request.content)
    assert body["goal"] == 3
    assert body["amount"] == "100.00"
    assert body["date"] == "2026-07-24"


@respx.mock
def test_add_contribution_default_date_today(client):
    route = respx.post("http://test/api/v1/goal-contributions/")
    route.respond(201, json={"id": 51, "goal": 3, "amount": "50.00"})
    r = add_goal_contribution(client, goal_id=3, amount="50.00")
    assert r["ok"] is True
    body = json.loads(route.calls.last.request.content)
    assert "date" in body
    # Should be today's date in YYYY-MM-DD
    assert len(body["date"]) == 10


@respx.mock
def test_add_contribution_empty_amount(client):
    r = add_goal_contribution(client, goal_id=3, amount="")
    assert r["ok"] is False
    assert "amount" in r["error"].lower()


@respx.mock
def test_add_contribution_api_error(client):
    respx.post("http://test/api/v1/goal-contributions/").respond(
        400, json={"goal": ["Meta não pertence ao usuário."]}
    )
    r = add_goal_contribution(client, goal_id=999, amount="100.00")
    assert r["ok"] is False
    assert "rejeitou" in r["error"]


@respx.mock
def test_add_contribution_goal_not_found(client):
    respx.post("http://test/api/v1/goal-contributions/").respond(404, json={"detail": "Not found"})
    r = add_goal_contribution(client, goal_id=0, amount="100.00")
    assert r["ok"] is False
    assert "não encontrado" in r["error"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd mcp && .venv/bin/python -m pytest tests/test_tools_goals_contribution.py -v`
Expected: FAIL — função não existe

- [ ] **Step 3: Write minimal implementation**

Adicionar em `mcp/finanpy_mcp/tools/goals.py`:

```python
from datetime import date as _date

from ..helpers import _result, _safe_call, _filter_params, _clean_text


def add_goal_contribution(client, goal_id, amount, date=None) -> dict:
    """Add a contribution to a savings goal."""
    amount_str = str(amount or "").strip()
    if not amount_str:
        return {"ok": False, "error": "amount é obrigatório."}

    if date is None:
        date = _date.today().isoformat()

    body = {
        "goal": goal_id,
        "amount": amount_str,
        "date": date,
    }
    return _safe_call(lambda: _result(
        "goal-contributions",
        client.request("POST", "goal-contributions/", json=body),
        body,
    ))
```

Adicionar dentro de `register_goal_tools` (após `finanpy_list_goals`):

```python
    @mcp.tool()
    def finanpy_add_goal_contribution(
        goal_id: int,
        amount: str,
        date: str | None = None,
    ) -> dict:
        """Adiciona um aporte a uma meta financeira.

        Args:
            goal_id: ID da meta
            amount: Valor do aporte (ex.: "100.00")
            date: Data no formato YYYY-MM-DD (opcional, default = hoje)

        Returns:
            {ok, endpoint, params, payload} — payload tem {id, goal, amount, date}
        """
        return add_goal_contribution(client, goal_id=goal_id, amount=amount, date=date)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd mcp && .venv/bin/python -m pytest tests/test_tools_goals_contribution.py -v`
Expected: PASS — 5 testes

- [ ] **Step 5: Commit**

```bash
git add mcp/finanpy_mcp/tools/goals.py mcp/tests/test_tools_goals_contribution.py
git commit -m "feat(mcp): add add_goal_contribution tool with default date today"
```

---

## Task 18: Full test suite run + server smoke

**Files:** none — verification only

- [ ] **Step 1: Run all MCP tests**

Run: `cd mcp && .venv/bin/python -m pytest tests/ -v`
Expected: All tests pass (Parte 1 + Parte 2 + Parte 3 = ~80+ testes)

- [ ] **Step 2: Verify server imports without error**

Run: `cd mcp && .venv/bin/python -c "from finanpy_mcp.server import mcp; print('OK', mcp.name)"`
Expected: `OK finanpy`

- [ ] **Step 3: List registered tools**

Run: `cd mcp && .venv/bin/python -c "
from finanpy_mcp.server import mcp
tools = mcp._tool_manager._tools
for name in sorted(tools.keys()):
    print(name)
print(f'Total: {len(tools)}')
"`
Expected: 19 tools listed, starting with `finanpy_`

- [ ] **Step 4: Commit (if any files were adjusted)**

Se ajustes foram feitos:
```bash
git add -A
git commit -m "test(mcp): full suite green — 19 tools registered"
```

---

## Task 19: Smoke script

**Files:**
- Create: `mcp/finanpy_mcp/smoke.py`

- [ ] **Step 1: Write implementation**

Criar `mcp/finanpy_mcp/smoke.py`:

```python
#!/usr/bin/env python3
"""Smoke test — runs post-deploy to verify MCP can reach the FinanPy API.

Exit 0 = all good. Exit 1 = something broke.
"""
import sys

from .config import get_config
from .http_client import FinanPyClient
from .tools.health import health
from .tools.reports import dashboard_snapshot


def main():
    try:
        cfg = get_config()
    except ValueError as e:
        print(f"FAIL: config error: {e}", file=sys.stderr)
        return 1

    client = FinanPyClient(
        base_url=cfg.base_url,
        token=cfg.token,
        timeout=cfg.timeout_seconds,
    )

    print("Testing health...")
    r = health(client)
    if r.get("ok"):
        print(f"  OK: {r['payload']}")
    else:
        print(f"  FAIL: {r.get('error')}", file=sys.stderr)
        return 1

    print("Testing dashboard_snapshot...")
    r = dashboard_snapshot(client)
    if r.get("ok"):
        print(f"  OK: {r['payload'].get('totals', {})}")
    else:
        print(f"  FAIL: {r.get('error')}", file=sys.stderr)
        return 1

    print("All smoke tests passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Verify it runs (will fail without env, which is correct)**

Run: `cd mcp && .venv/bin/python -m finanpy_mcp.smoke 2>&1 || true`
Expected: Output with "FAIL: config error" because no env vars set in terminal

- [ ] **Step 3: Commit**

```bash
git add mcp/finanpy_mcp/smoke.py
git commit -m "feat(mcp): add smoke.py for post-deploy verification"
```

---

## Task 20: Setup script (create hermes user + DRF Token)

**Files:**
- Create: `mcp/scripts/setup_hermes_user.sh`

- [ ] **Step 1: Write script**

Criar `mcp/scripts/setup_hermes_user.sh`:

```bash
#!/usr/bin/env bash
# Cria o user Django "hermes" e gera um DRF Token na FinanPy VPS.
# Rodar uma única vez. Guardar o token no config.yaml do Hermes.

set -euo pipefail

CONTAINER="${FINANPY_CONTAINER:-finanpy-web-1}"

echo "Criando user hermes no Django..."
docker exec -it "$CONTAINER" python manage.py shell <<'PY'
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token

U = get_user_model()
u, created = U.objects.get_or_create(
    username='hermes',
    defaults={
        'email': 'hermes@finanpy.local',
        'is_active': True,
    }
)
t, _ = Token.objects.get_or_create(user=u)
action = 'Criado' if created else 'Já existia'
print(f'{action} user hermes (id={u.id}).')
print(f'DRF Token: {t.key}')
PY
```

- [ ] **Step 2: Make executable**

```bash
chmod +x mcp/scripts/setup_hermes_user.sh
```

- [ ] **Step 3: Commit**

```bash
git add mcp/scripts/setup_hermes_user.sh
git commit -m "feat(mcp): add setup_hermes_user.sh for DRF Token generation"
```

---

## Task 21: Deploy script

**Files:**
- Create: `mcp/scripts/deploy_vps.sh`

- [ ] **Step 1: Write script**

Criar `mcp/scripts/deploy_vps.sh`:

```bash
#!/usr/bin/env bash
# Deploy do MCP FinanPy para a VPS via rsync + restart Hermes.
# Uso: bash mcp/scripts/deploy_vps.sh

set -euo pipefail

VPS_HOST="${VPS_HOST:-root@38.52.128.62}"
SRC="$(git rev-parse --show-toplevel)/mcp/"
DST="/opt/finanpy-mcp/"

echo "=== 1. Validação local — testes ==="
cd "$(git rev-parse --show-toplevel)/mcp"
.venv/bin/python -m pytest tests/ -q

echo "=== 2. Sincronia — rsync ==="
rsync -avz --delete \
  --exclude='.venv' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='.env' \
  "$SRC" "$VPS_HOST:$DST"

echo "=== 3. Reinstala deps ==="
ssh "$VPS_HOST" "cd /opt/finanpy-mcp && .venv/bin/pip install -e . -q"

echo "=== 4. Restart Hermes ==="
ssh "$VPS_HOST" 'systemctl restart hermes-gateway'

echo "=== 5. Smoke ==="
ssh "$VPS_HOST" '/opt/finanpy-mcp/.venv/bin/python -m finanpy_mcp.smoke' \
  || { echo "FAIL: smoke falhou — verifique FINANPY_API_TOKEN no config.yaml do Hermes"; exit 1; }

echo "=== Deploy OK ==="
```

- [ ] **Step 2: Make executable**

```bash
chmod +x mcp/scripts/deploy_vps.sh
```

- [ ] **Step 3: Commit**

```bash
git add mcp/scripts/deploy_vps.sh
git commit -m "feat(mcp): add deploy_vps.sh with rsync + test + smoke verification"
```

---

## Task 22: Update HERMES_CONFIG.md + final commit

**Files:**
- Modify: `mcp/HERMES_CONFIG.md`

- [ ] **Step 1: Rewrite HERMES_CONFIG.md**

Substituir conteúdo de `mcp/HERMES_CONFIG.md`:

```markdown
# Hermes Configuration for MCP FinanPy

## Neo (principal)

Adicionar ao `config.yaml` do Neo principal:

```yaml
mcp_servers:
  finanpy:
    command: /opt/finanpy-mcp/.venv/bin/python
    args:
      - /opt/finanpy-mcp/run_mcp.py
    timeout: 60
    connect_timeout: 30
    env:
      FINANPY_API_BASE_URL: http://127.0.0.1:8001/api/v1/
      FINANPY_API_TOKEN: <cole-aqui-o-token-do-user-hermes>
    enabled: true
```

## agente-braba

**NÃO** adicionar `mcp_servers.finanpy` ao profile do agente-braba.
Este profile é usado para outras tarefas (Brabus store, etc.) e não deve
acessar o FinanPy. A política de `mcp_exclude` no perfil garante isolamento.

## Setup do user hermes (uma única vez)

```bash
# Na VPS, dentro do container FinanPy:
bash mcp/scripts/setup_hermes_user.sh
# Copiar o token exibido para FINANPY_API_TOKEN no config.yaml acima.
```

## Rotacionamento do token

Para rotacionar o DRF Token do user hermes:

```bash
# 1. Revogar token atual
docker exec -it finanpy-web-1 python manage.py shell -c "
from rest_framework.authtoken.models import Token
from django.contrib.auth import get_user_model
U = get_user_model()
u = U.objects.get(username='hermes')
Token.objects.filter(user=u).delete()
print('Token revogado.')
"

# 2. Gerar novo token
bash mcp/scripts/setup_hermes_user.sh

# 3. Atualizar FINANPY_API_TOKEN no config.yaml do Hermes

# 4. Reiniciar Hermes
ssh root@38.52.128.62 'systemctl restart hermes-gateway'
```

## Deploy manual

```bash
# A partir do repositório local:
bash mcp/scripts/deploy_vps.sh
```

O script:
1. Roda os testes locais
2. Faz rsync para /opt/finanpy-mcp/ na VPS
3. Reinstala as deps na venv
4. Reinicia o hermes-gateway
5. Roda o smoke test
```

- [ ] **Step 2: Commit**

```bash
git add mcp/HERMES_CONFIG.md
git commit -m "docs(mcp): update HERMES_CONFIG.md with v1.1 API-based config and rotation steps"
```

---

## Fim da Parte 3 — Plano Completo

Todas as 19 tools implementadas e testadas:

| # | Tool | Task |
|---|---|---|
| 1 | finanpy_health | 8 |
| 2 | finanpy_dashboard_snapshot | 11 |
| 3 | finanpy_monthly_summary | 11 |
| 4 | finanpy_yearly_summary | 11 |
| 5 | finanpy_list_accounts | 8 |
| 6 | finanpy_list_categories | 9 |
| 7 | finanpy_list_subcategories | 9 |
| 8 | finanpy_create_category | 13 |
| 9 | finanpy_update_category | 13 |
| 10 | finanpy_list_tags | 9 |
| 11 | finanpy_create_tag | 14 |
| 12 | finanpy_update_tag | 14 |
| 13 | finanpy_list_transactions | 10 |
| 14 | finanpy_register_quick_transaction | 15 |
| 15 | finanpy_confirm_pending_transaction | 16 |
| 16 | finanpy_list_budgets | 12 |
| 17 | finanpy_list_goals | 12 |
| 18 | finanpy_get_monthly_plan | 12 |
| 19 | finanpy_add_goal_contribution | 17 |

Infra:
- smoke.py (Task 19)
- setup_hermes_user.sh (Task 20)
- deploy_vps.sh (Task 21)
- HERMES_CONFIG.md (Task 22)