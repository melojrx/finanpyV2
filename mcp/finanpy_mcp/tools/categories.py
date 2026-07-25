"""Category-related MCP tools."""
import re

from ..helpers import _result, _safe_call, _filter_params, _clean_text


_CATEGORY_TYPE_CHOICES = {"INCOME", "EXPENSE"}
_COLOR_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")


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


def create_category(
    client,
    name,
    category_type,
    color="#10B981",
    icon="💰",
    parent=None,
    is_active=True,
) -> dict:
    """Create a new category or subcategory."""
    name = _clean_text(name, max_len=50)
    if not name:
        return {"ok": False, "error": "name é obrigatório."}
    if category_type not in _CATEGORY_TYPE_CHOICES:
        return {"ok": False, "error": f"category_type deve ser um de {sorted(_CATEGORY_TYPE_CHOICES)}."}
    if not _COLOR_RE.match(color):
        return {"ok": False, "error": "color deve ser um hex válido (ex.: #10B981)."}
    icon = _clean_text(icon, max_len=10)

    body = {
        "name": name,
        "category_type": category_type,
        "color": color,
        "icon": icon,
        "is_active": is_active,
    }
    if parent is not None:
        body["parent"] = parent

    return _safe_call(lambda: _result(
        "categories/create",
        client.request("POST", "categories/", json=body),
        body,
    ))


def update_category(
    client,
    id,
    name=None,
    category_type=None,
    color=None,
    icon=None,
    parent=None,
    is_active=None,
) -> dict:
    """Update fields of an existing category (partial update)."""
    body = {}
    if name is not None:
        name = _clean_text(name, max_len=50)
        if not name:
            return {"ok": False, "error": "name não pode ser vazio."}
        body["name"] = name
    if category_type is not None:
        if category_type not in _CATEGORY_TYPE_CHOICES:
            return {"ok": False, "error": f"category_type deve ser um de {sorted(_CATEGORY_TYPE_CHOICES)}."}
        body["category_type"] = category_type
    if color is not None:
        if not _COLOR_RE.match(color):
            return {"ok": False, "error": "color deve ser um hex válido (ex.: #10B981)."}
        body["color"] = color
    if icon is not None:
        body["icon"] = _clean_text(icon, max_len=10)
    if parent is not None:
        body["parent"] = parent
    if is_active is not None:
        body["is_active"] = is_active

    if not body:
        return {"ok": False, "error": "Nada para atualizar — forneça ao menos um campo."}

    return _safe_call(lambda: _result(
        "categories/update",
        client.request("PATCH", f"categories/{id}/", json=body),
        {"id": id, **body},
    ))


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

    @mcp.tool()
    def finanpy_create_category(
        name: str,
        category_type: str,
        color: str = "#10B981",
        icon: str = "💰",
        parent: int | None = None,
        is_active: bool = True,
    ) -> dict:
        """Cria uma nova categoria ou subcategoria.

        Args:
            name: Nome da categoria (máx 50 caracteres)
            category_type: "INCOME" ou "EXPENSE"
            color: Hex color (ex.: "#10B981"). Default: verde
            icon: Emoji (ex.: "🍔"). Default: 💰
            parent: ID da categoria pai (para subcategoria). Opcional.
            is_active: True (default) para ativa

        Returns:
            {ok, endpoint, params, payload} — payload tem {id, name, ...}
        """
        return create_category(
            client, name=name, category_type=category_type,
            color=color, icon=icon, parent=parent, is_active=is_active,
        )

    @mcp.tool()
    def finanpy_update_category(
        id: int,
        name: str | None = None,
        category_type: str | None = None,
        color: str | None = None,
        icon: str | None = None,
        parent: int | None = None,
        is_active: bool | None = None,
    ) -> dict:
        """Atualiza campos de uma categoria existente (partial update).

        Use is_active=False para desativar (soft-delete) em vez de deletar.

        Args:
            id: ID da categoria
            name: Novo nome (opcional)
            category_type: "INCOME" ou "EXPENSE" (opcional)
            color: Novo hex color (opcional)
            icon: Novo emoji (opcional)
            parent: Novo ID pai (opcional)
            is_active: True/False para ativar/desativar (opcional)

        Returns:
            {ok, endpoint, params, payload} — payload tem a categoria atualizada
        """
        return update_category(
            client, id=id, name=name, category_type=category_type,
            color=color, icon=icon, parent=parent, is_active=is_active,
        )