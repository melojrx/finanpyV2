"""MCP FinanPy Server."""
from mcp.server import Server
from mcp.server.stdio import stdio_server

from .config import get_config
from .client import FinanPyClient
from .tools.accounts import register_account_tools
from .tools.transactions import register_transaction_tools
from .tools.categories import register_category_tools
from .tools.budgets import register_budget_tools
from .tools.goals import register_goal_tools
from .tools.plans import register_plan_tools
from .tools.reports import register_report_tools


def create_server() -> Server:
    """Create and configure MCP server."""
    config = get_config()
    client = FinanPyClient(config)

    server = Server("finanpy-mcp")

    # Register all tools
    register_account_tools(server, config)
    register_transaction_tools(server, config)
    register_category_tools(server, config)
    register_budget_tools(server, config)
    register_goal_tools(server, config)
    register_plan_tools(server, config)
    register_report_tools(server, config)

    return server


async def main():
    """Run the MCP server."""
    server = create_server()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())