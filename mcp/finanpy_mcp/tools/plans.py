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