"""MCP FinanPy Server."""
import logging

from mcp.server.fastmcp import FastMCP

from .config import get_config
from .http_client import FinanPyClient
from .tools.health import register_health_tools
from .tools.accounts import register_account_tools
from .tools.categories import register_category_tools
from .tools.tags import register_tag_tools
from .tools.transactions import register_transaction_tools
from .tools.reports import register_report_tools
from .tools.budgets import register_budget_tools
from .tools.goals import register_goal_tools
from .tools.plans import register_plan_tools

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

mcp = FastMCP("finanpy")


def _get_client() -> FinanPyClient:
    cfg = get_config()
    return FinanPyClient(
        base_url=cfg.base_url,
        token=cfg.token,
        timeout=cfg.timeout_seconds,
    )


def _register_all():
    client = _get_client()
    register_health_tools(mcp, client)
    register_account_tools(mcp, client)
    register_category_tools(mcp, client)
    register_tag_tools(mcp, client)
    register_transaction_tools(mcp, client)
    register_report_tools(mcp, client)
    register_budget_tools(mcp, client)
    register_goal_tools(mcp, client)
    register_plan_tools(mcp, client)


def main():
    """Run the MCP server (stdio transport)."""
    _register_all()
    mcp.run()


if __name__ == "__main__":
    main()