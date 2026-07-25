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