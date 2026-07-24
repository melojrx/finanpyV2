"""Tag-related MCP tools."""
from ..helpers import _result, _safe_call


def list_tags(client) -> dict:
    """List all tags."""
    return _safe_call(lambda: _result(
        "tags",
        client.request("GET", "tags/"),
    ))


def register_tag_tools(mcp, client):
    """Register tag tools with MCP server."""

    @mcp.tool()
    def finanpy_list_tags() -> dict:
        """Lista todas as tags do usuário.

        Returns:
            {ok, endpoint, params, payload} — payload.results é
            [{id, name, created_at}, ...]
        """
        return list_tags(client)