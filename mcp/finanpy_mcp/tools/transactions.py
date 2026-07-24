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