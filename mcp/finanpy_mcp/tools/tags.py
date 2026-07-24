"""Tag-related MCP tools."""
from ..helpers import _result, _safe_call, _clean_text


def list_tags(client) -> dict:
    """List all tags."""
    return _safe_call(lambda: _result(
        "tags",
        client.request("GET", "tags/"),
    ))


def create_tag(client, name) -> dict:
    """Create a new tag. Name is normalized to lowercase/strip."""
    name = _clean_text(name, max_len=50).lower()
    if not name:
        return {"ok": False, "error": "name não pode ser vazio."}
    body = {"name": name}
    return _safe_call(lambda: _result(
        "tags/create",
        client.request("POST", "tags/", json=body),
        body,
    ))


def update_tag(client, id, name) -> dict:
    """Update a tag's name. Name is normalized to lowercase/strip."""
    name = _clean_text(name, max_len=50).lower()
    if not name:
        return {"ok": False, "error": "name não pode ser vazio."}
    body = {"name": name}
    return _safe_call(lambda: _result(
        "tags/update",
        client.request("PATCH", f"tags/{id}/", json=body),
        {"id": id, **body},
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

    @mcp.tool()
    def finanpy_create_tag(name: str) -> dict:
        """Cria uma nova tag. O nome é normalizado (lowercase, sem espaços extras).

        Args:
            name: Nome da tag (máx 50 caracteres, normalizado para lowercase)

        Returns:
            {ok, endpoint, params, payload} — payload tem {id, name, created_at}
        """
        return create_tag(client, name=name)

    @mcp.tool()
    def finanpy_update_tag(id: int, name: str) -> dict:
        """Atualiza o nome de uma tag existente.

        Args:
            id: ID da tag
            name: Novo nome (normalizado para lowercase, máx 50 chars)

        Returns:
            {ok, endpoint, params, payload} — payload tem a tag atualizada
        """
        return update_tag(client, id=id, name=name)