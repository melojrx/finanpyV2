"""Monthly plan-related MCP tools."""
from ..client import FinanPyClient


def register_plan_tools(mcp, config):
    """Register plan tools with MCP server."""
    client = FinanPyClient(config)

    @mcp.tool()
    def finanpy_get_monthly_plan(year: int, month: int) -> dict:
        """Get monthly plan with items.

        Args:
            year: Year
            month: Month

        Returns:
            Monthly plan: {id, status, renda, teto, items}
        """
        # TODO: Implement when MonthlyPlan model is confirmed
        return {"id": None, "status": None, "renda": "0", "teto": "0", "items": []}

    @mcp.tool()
    def finanpy_upsert_plan_item(year: int, month: int, category: int, planned_amount: str) -> dict:
        """Create or update a monthly plan item.

        Args:
            year: Year
            month: Month
            category: Category ID
            planned_amount: Planned amount

        Returns:
            Updated item: {id, amount}
        """
        # TODO: Implement when MonthlyPlan model is confirmed
        return {"id": None, "amount": planned_amount}