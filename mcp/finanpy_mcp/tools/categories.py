"""Category-related MCP tools."""
from ..client import FinanPyClient


def register_category_tools(mcp, config):
    """Register category tools with MCP server."""
    client = FinanPyClient(config)

    @mcp.tool()
    def finanpy_get_categories(category_type: str | None = None) -> list[dict]:
        """Get all categories, optionally filtered by type.

        Args:
            category_type: "INCOME" or "EXPENSE" (optional)

        Returns:
            List of categories: [{id, name, parent_name, icon}, ...]
        """
        categories = client.get_categories(category_type)
        return [
            {
                "id": c.id,
                "name": c.name,
                "parent_name": c.parent_name,
                "icon": c.icon,
            }
            for c in categories
        ]