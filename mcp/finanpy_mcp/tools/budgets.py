"""Budget-related MCP tools."""
from ..client import FinanPyClient


def register_budget_tools(mcp, config):
    """Register budget tools with MCP server."""
    client = FinanPyClient(config)

    @mcp.tool()
    def finanpy_get_budgets(year: int | None = None, month: int | None = None) -> list[dict]:
        """Get budgets with spending status.

        Args:
            year: Filter by year (default: current year)
            month: Filter by month (default: current month)

        Returns:
            List of budgets: [{category, planned, spent, percentage}, ...]
        """
        # TODO: Implement when Budget model is confirmed
        return []

    @mcp.tool()
    def finanpy_get_budget_status(category_id: int, year: int | None = None, month: int | None = None) -> dict:
        """Get budget status for a specific category.

        Args:
            category_id: Category ID
            year: Year (default: current)
            month: Month (default: current)

        Returns:
            Budget status: {planned, spent, remaining, percentage}
        """
        # TODO: Implement when Budget model is confirmed
        return {"planned": "0", "spent": "0", "remaining": "0", "percentage": 0}
