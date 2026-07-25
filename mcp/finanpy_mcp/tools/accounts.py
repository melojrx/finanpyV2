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