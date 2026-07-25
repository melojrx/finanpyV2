"""Health-related MCP tools."""
from ..helpers import _result, _safe_call


def health(client) -> dict:
    """Check FinanPy API connectivity and auth."""
    def _do():
        client.request("GET", "accounts/")
        return _result("health", {"status": "ok"})
    return _safe_call(_do)


def register_health_tools(mcp, client):
    """Register health tools with MCP server."""

    @mcp.tool()
    def finanpy_health() -> dict:
        """Verifica se a API do FinanPy está acessível e o token é válido."""
        return health(client)