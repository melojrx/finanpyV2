import pytest
import respx
from finanpy_mcp.tools.categories import list_categories, list_subcategories
from finanpy_mcp.tools.tags import list_tags
from finanpy_mcp.http_client import FinanPyClient


@pytest.fixture
def client():
    return FinanPyClient(
        base_url="http://test/api/v1/",
        token="t" * 40,
        timeout=5.0,
    )


CATEGORIES_DATA = [
    {"id": 1, "name": "Alimentação", "category_type": "EXPENSE", "parent": None, "icon": "🍔"},
    {"id": 2, "name": "Restaurantes", "category_type": "EXPENSE", "parent": 1, "icon": "🍽️"},
    {"id": 3, "name": "Salário", "category_type": "INCOME", "parent": None, "icon": "💰"},
]


@respx.mock
def test_list_categories_all(client):
    respx.get("http://test/api/v1/categories/").respond(200, json={"results": CATEGORIES_DATA})
    r = list_categories(client)
    assert r["ok"] is True
    assert len(r["payload"]["results"]) == 3


@respx.mock
def test_list_categories_by_type(client):
    route = respx.get("http://test/api/v1/categories/")
    route.respond(200, json={"results": [CATEGORIES_DATA[2]]})
    r = list_categories(client, category_type="INCOME")
    assert r["ok"] is True
    assert r["params"] == {"type": "INCOME"}
    assert route.calls.last.request.url.params["type"] == "INCOME"


@respx.mock
def test_list_subcategories_by_parent(client):
    respx.get("http://test/api/v1/categories/").respond(200, json={"results": CATEGORIES_DATA})
    r = list_subcategories(client, parent_id=1)
    assert r["ok"] is True
    assert r["params"] == {"parent_id": 1}
    results = r["payload"]["results"]
    assert len(results) == 1
    assert results[0]["id"] == 2
    assert results[0]["name"] == "Restaurantes"


@respx.mock
def test_list_subcategories_no_parent_returns_tree(client):
    respx.get("http://test/api/v1/categories/").respond(200, json={"results": CATEGORIES_DATA})
    r = list_subcategories(client)
    assert r["ok"] is True
    roots = r["payload"]["results"]
    assert len(roots) == 2  # Alimentação + Salário (no parent)
    alimentacao = [c for c in roots if c["id"] == 1][0]
    assert len(alimentacao["children"]) == 1
    assert alimentacao["children"][0]["id"] == 2


@respx.mock
def test_list_tags(client):
    respx.get("http://test/api/v1/tags/").respond(200, json={
        "results": [{"id": 1, "name": "recorrente", "created_at": "2026-07-01T00:00:00Z"}]
    })
    r = list_tags(client)
    assert r["ok"] is True
    assert r["payload"]["results"][0]["name"] == "recorrente"


@respx.mock
def test_list_categories_error(client):
    respx.get("http://test/api/v1/categories/").respond(500, json={"error": "boom"})
    r = list_categories(client)
    assert r["ok"] is False
    assert "HTTP 500" in r["error"]