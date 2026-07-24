"""Category-related MCP tools."""
from ..helpers import _result, _safe_call, _filter_params


def list_categories(client, category_type=None) -> dict:
    """List all active categories, optionally filtered by type."""
    params = _filter_params({"type": category_type})
    return _safe_call(lambda: _result(
        "categories",
        client.request("GET", "categories/", params=params or None),
        params,
    ))


def _build_tree(cats: list) -> list:
    by_id = {c["id"]: {**c, "children": []} for c in cats if "id" in c}
    roots = []
    for c in cats:
        cid = c.get("id")
        parent = c.get("parent")
        if cid not in by_id:
            continue
        if parent and parent in by_id:
            by_id[parent]["children"].append(by_id[cid])
        elif not parent:
            roots.append(by_id[cid])
    return roots


def list_subcategories(client, parent_id=None) -> dict:
    """List subcategories (children) by parent_id, or the full tree if omitted."""
    def _do():
        payload = client.request("GET", "categories/")
        data = payload.get("results", payload) if isinstance(payload, dict) else payload
        if not isinstance(data, list):
            data = []
        if parent_id is not None:
            filtered = [c for c in data if c.get("parent") == parent_id]
            return _result("subcategories", {"results": filtered}, {"parent_id": parent_id})
        tree = _build_tree(data)
        return _result("subcategories", {"results": tree}, {})
    return _safe_call(_do)


def register_category_tools(mcp, client):
    """Register category tools with MCP server."""

    @mcp.tool()
    def finanpy_list_categories(category_type: str | None = None) -> dict:
        """Lista categorias ativas, opcionalmente filtradas por tipo.

        Args:
            category_type: "INCOME" ou "EXPENSE" (opcional)

        Returns:
            {ok, endpoint, params, payload} — payload.results é
            [{id, name, category_type, parent, color, icon, is_active}, ...]
        """
        return list_categories(client, category_type=category_type)

    @mcp.tool()
    def finanpy_list_subcategories(parent_id: int | None = None) -> dict:
        """Lista subcategorias filhas de parent_id, ou a árvore completa.

        Args:
            parent_id: ID da categoria pai (opcional). Se omitido,
                       devolve a hierarquia completa em `children`.

        Returns:
            {ok, endpoint, params, payload} — payload.results é
            [{id, name, children: [...]}, ...]
        """
        return list_subcategories(client, parent_id=parent_id)