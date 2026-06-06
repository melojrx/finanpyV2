"""Transaction-related MCP tools."""
from ..client import FinanPyClient


def register_transaction_tools(mcp, config):
    """Register transaction tools with MCP server."""
    client = FinanPyClient(config)

    @mcp.tool()
    def finanpy_register_transaction(
        transaction_type: str,
        amount: str,
        description: str,
        transaction_date: str,
        account: int,
        category: int,
        notes: str = "",
    ) -> dict:
        """Register a new transaction (expense or income).

        Args:
            transaction_type: "EXPENSE" or "INCOME"
            amount: Amount as string (e.g., "50.00")
            description: Transaction description
            transaction_date: Date in YYYY-MM-DD format
            account: Account ID (1=Caixa, 2=Mercado Pago)
            category: Category ID
            notes: Optional notes

        Returns:
            Created transaction with new balance: {id, balance}
        """
        result = client.register_transaction(
            transaction_type=transaction_type,
            amount=amount,
            description=description,
            transaction_date=transaction_date,
            account=account,
            category=category,
            notes=notes,
        )
        return {"id": result.id, "balance": result.balance}

    @mcp.tool()
    def finanpy_get_transactions(
        year: int | None = None,
        month: int | None = None,
        account: int | None = None,
        transaction_type: str | None = None,
        category: int | None = None,
        limit: int = 50,
    ) -> list[dict]:
        """Get transactions with optional filters.

        Args:
            year: Filter by year
            month: Filter by month
            account: Filter by account ID
            transaction_type: "EXPENSE" or "INCOME"
            category: Filter by category ID
            limit: Max results (default 50)

        Returns:
            List of transactions: [{id, date, type, amount, description, category}, ...]
        """
        return client.get_transactions(
            year=year,
            month=month,
            account=account,
            transaction_type=transaction_type,
            category=category,
            limit=limit,
        )