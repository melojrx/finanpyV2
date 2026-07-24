import json
import pytest
import respx
from finanpy_mcp.tools.categories import create_category, update_category
from finanpy_mcp.http_client import FinanPyClient


@pytest.fixture
def client():
    return FinanPyClient(
        base_url="http://test/api/v1/",
        token="t" * 40,
        timeout=5.0,
    )


@respx.mock
def test_create_category_minimal(client):
    route = respx.post("http://test/api/v1/categories/")
    route.respond(201, json={"id": 5, "name": "Mercado", "category_type": "EXPENSE"})
    r = create_category(client, name="Mercado", category_type="EXPENSE")
    assert r["ok"] is True
    assert r["payload"]["id"] == 5
    body = json.loads(route.calls.last.request.content)
    assert body["name"] == "Mercado"
    assert body["category_type"] == "EXPENSE"
    assert body["color"] == "#10B981"
    assert body["icon"] == "💰"
    assert body["is_active"] is True
    assert "parent" not in body or body["parent"] is None


@respx.mock
def test_create_category_with_parent(client):
    route = respx.post("http://test/api/v1/categories/")
    route.respond(201, json={"id": 6, "name": "Padaria", "category_type": "EXPENSE"})
    r = create_category(client, name="Padaria", category_type="EXPENSE", parent=5, color="#EF4444", icon="🍞")
    assert r["ok"] is True
    body = json.loads(route.calls.last.request.content)
    assert body["parent"] == 5
    assert body["color"] == "#EF4444"
    assert body["icon"] == "🍞"


@respx.mock
def test_create_category_invalid_type(client):
    r = create_category(client, name="X", category_type="INVALIDO")
    assert r["ok"] is False
    assert "category_type" in r["error"]


@respx.mock
def test_create_category_invalid_color(client):
    r = create_category(client, name="X", category_type="EXPENSE", color="red")
    assert r["ok"] is False
    assert "color" in r["error"]


@respx.mock
def test_create_category_name_truncated(client):
    route = respx.post("http://test/api/v1/categories/")
    route.respond(201, json={"id": 7})
    long_name = "x" * 100
    r = create_category(client, name=long_name, category_type="EXPENSE")
    assert r["ok"] is True
    body = json.loads(route.calls.last.request.content)
    assert len(body["name"]) == 50


@respx.mock
def test_create_category_api_error(client):
    respx.post("http://test/api/v1/categories/").respond(400, json={"name": ["This field is required."]})
    r = create_category(client, name="X", category_type="EXPENSE")
    assert r["ok"] is False
    assert "rejeitou" in r["error"]


@respx.mock
def test_update_category_partial(client):
    route = respx.patch("http://test/api/v1/categories/5/")
    route.respond(200, json={"id": 5, "name": "Alimentação Atualizada"})
    r = update_category(client, id=5, name="Alimentação Atualizada")
    assert r["ok"] is True
    body = json.loads(route.calls.last.request.content)
    assert body == {"name": "Alimentação Atualizada"}


@respx.mock
def test_update_category_deactivate(client):
    route = respx.patch("http://test/api/v1/categories/3/")
    route.respond(200, json={"id": 3, "is_active": False})
    r = update_category(client, id=3, is_active=False)
    assert r["ok"] is True
    body = json.loads(route.calls.last.request.content)
    assert body == {"is_active": False}


@respx.mock
def test_update_category_no_fields(client):
    r = update_category(client, id=5)
    assert r["ok"] is False
    assert "nada" in r["error"].lower() or "no field" in r["error"].lower()


@respx.mock
def test_update_category_api_error(client):
    respx.patch("http://test/api/v1/categories/999/").respond(404, json={"detail": "Not found"})
    r = update_category(client, id=999, name="X")
    assert r["ok"] is False
    assert "não encontrado" in r["error"]