import json
import pytest
import respx
from finanpy_mcp.tools.tags import create_tag, update_tag
from finanpy_mcp.http_client import FinanPyClient


@pytest.fixture
def client():
    return FinanPyClient(
        base_url="http://test/api/v1/",
        token="t" * 40,
        timeout=5.0,
    )


@respx.mock
def test_create_tag_normalizes_lower(client):
    route = respx.post("http://test/api/v1/tags/")
    route.respond(201, json={"id": 1, "name": "recorrente"})
    r = create_tag(client, name="  RECORRENTE  ")
    assert r["ok"] is True
    body = json.loads(route.calls.last.request.content)
    assert body == {"name": "recorrente"}


@respx.mock
def test_create_tag_empty_returns_error(client):
    r = create_tag(client, name="   ")
    assert r["ok"] is False
    assert "name" in r["error"].lower() or "vazio" in r["error"].lower()


@respx.mock
def test_create_tag_truncates(client):
    route = respx.post("http://test/api/v1/tags/")
    route.respond(201, json={"id": 2, "name": "x" * 50})
    r = create_tag(client, name="x" * 100)
    assert r["ok"] is True
    body = json.loads(route.calls.last.request.content)
    assert len(body["name"]) == 50


@respx.mock
def test_create_tag_api_duplicate(client):
    respx.post("http://test/api/v1/tags/").respond(400, json={"name": ["Tag com este nome já existe."]})
    r = create_tag(client, name="recorrente")
    assert r["ok"] is False
    assert "rejeitou" in r["error"]


@respx.mock
def test_update_tag(client):
    route = respx.patch("http://test/api/v1/tags/3/")
    route.respond(200, json={"id": 3, "name": "novo-nome"})
    r = update_tag(client, id=3, name="  NOVO-NOME  ")
    assert r["ok"] is True
    body = json.loads(route.calls.last.request.content)
    assert body == {"name": "novo-nome"}


@respx.mock
def test_update_tag_empty_name(client):
    r = update_tag(client, id=3, name="")
    assert r["ok"] is False
    assert "vazio" in r["error"].lower()


@respx.mock
def test_update_tag_api_error(client):
    respx.patch("http://test/api/v1/tags/999/").respond(404, json={"detail": "Not found"})
    r = update_tag(client, id=999, name="x")
    assert r["ok"] is False
    assert "não encontrado" in r["error"]