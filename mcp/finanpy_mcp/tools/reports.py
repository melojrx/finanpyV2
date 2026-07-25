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