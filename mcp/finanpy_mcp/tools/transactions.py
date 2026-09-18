"""Transaction-related MCP tools."""
import uuid

from ..helpers import _result, _safe_call, _filter_params, _safe_int


_TX_TYPE_CHOICES = {"INCOME", "EXPENSE"}


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


def confirm_pending_transaction(client, id) -> dict:
    """Confirm a pending transaction."""
    return _safe_call(lambda: _result(
        "transactions/confirm",
        client.request("POST", f"transactions/{id}/confirm/"),
        {"id": id},
    ))


def update_transaction(client, id, **changes) -> dict:
    body = {key: value for key, value in changes.items() if value is not None}
    return _safe_call(lambda: _result(
        'transactions', client.request('PATCH', f'transactions/{id}/', json=body), body,
    ))


def delete_transaction(client, id) -> dict:
    return _safe_call(lambda: _result(
        'transactions', client.request('DELETE', f'transactions/{id}/'), {'id': id},
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

    @mcp.tool()
    def finanpy_update_transaction(id: int, amount: str | None = None, description: str | None = None, transaction_date: str | None = None, status: str | None = None, account: int | None = None, category: int | None = None) -> dict:
        """Atualiza uma transação existente via PATCH autenticado."""
        return update_transaction(client, id, amount=amount, description=description,
                                  transaction_date=transaction_date, status=status,
                                  account=account, category=category)

    @mcp.tool()
    def finanpy_delete_transaction(id: int) -> dict:
        """Exclui uma transação; o backend reverte seu impacto de saldo."""
        return delete_transaction(client, id)
