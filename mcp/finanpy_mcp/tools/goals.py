"""Goal-related MCP tools."""
from datetime import date as _date

from ..helpers import _result, _safe_call, _filter_params


def list_goals(client, status=None) -> dict:
    """List savings goals, optionally filtered by status."""
    params = _filter_params({"status": status})
    return _safe_call(lambda: _result(
        "goals",
        client.request("GET", "goals/", params=params or None),
        params,
    ))


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