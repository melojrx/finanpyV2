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