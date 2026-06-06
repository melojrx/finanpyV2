"""Report-related MCP tools."""
from ..client import FinanPyClient


def register_report_tools(mcp, config):
    """Register report tools with MCP server."""
    client = FinanPyClient(config)

    @mcp.tool()
    def finanpy_monthly_summary(year: int, month: int) -> dict:
        """Get monthly financial summary.

        Args:
            year: Year
            month: Month

        Returns:
            Summary: {income, expenses, balance, count}
        """
        return client.monthly_summary(year, month)

    @mcp.tool()
    def finanpy_yearly_summary(year: int) -> list[dict]:
        """Get yearly summary by month.

        Args:
            year: Year

        Returns:
            Monthly summaries: [{month, income, expenses, balance}, ...]
        """
        return client.yearly_summary(year)

    @mcp.tool()
    def finanpy_pending_transactions(due: bool = False) -> list[dict]:
        """Get pending (unconfirmed) transactions.

        Args:
            due: Only show transactions due today or earlier

        Returns:
            List of pending transactions: [{id, date, amount, description}, ...]
        """
        # TODO: Implement when pending status is confirmed
        return []