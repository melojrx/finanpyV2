"""Account-related MCP tools."""
from ..client import FinanPyClient


def get_accounts(client: FinanPyClient) -> list[dict]:
    """Get all accounts with balances.

    Returns:
        List of accounts with id, name, balance, account_type.
    """
    accounts = client.get_accounts()
    return [
        {
            "id": a.id,
            "name": a.name,
            "balance": a.balance,
            "account_type": a.account_type,
        }
        for a in accounts
    ]


def register_account_tools(mcp, config):
    """Register account tools with MCP server."""
    client = FinanPyClient(config)

    @mcp.tool()
    def finanpy_get_accounts() -> list[dict]:
        """Get all accounts with their current balances.

        Returns:
            List of accounts: [{id, name, balance, account_type}, ...]
        """
        return get_accounts(client)
