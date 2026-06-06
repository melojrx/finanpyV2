"""Goal-related MCP tools."""
from ..client import FinanPyClient


def register_goal_tools(mcp, config):
    """Register goal tools with MCP server."""
    client = FinanPyClient(config)

    @mcp.tool()
    def finanpy_get_goals() -> list[dict]:
        """Get all savings goals with progress.

        Returns:
            List of goals: [{id, name, target, current, percentage, deadline}, ...]
        """
        # TODO: Implement when Goal model is confirmed
        return []

    @mcp.tool()
    def finanpy_add_contribution(goal_id: int, amount: str, date: str | None = None) -> dict:
        """Add a contribution to a savings goal.

        Args:
            goal_id: Goal ID
            amount: Contribution amount
            date: Date in YYYY-MM-DD format (default: today)

        Returns:
            Updated goal: {goal_id, new_balance, total_contributed}
        """
        # TODO: Implement when Goal model is confirmed
        return {"goal_id": goal_id, "new_balance": amount, "total_contributed": amount}