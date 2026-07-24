import httpx
import respx
import pytest
from finanpy_mcp.tools.health import health
from finanpy_mcp.tools.accounts import list_accounts
from finanpy_mcp.http_client import FinanPyClient


@pytest.fixture
def client():
    return FinanPyClient(
        base_url="http://test/api/v1/",
        token="t" * 40,
        timeout=5.0,
    )


@respx.mock
def test_health_ok(client):
    respx.get("http://test/api/v1/accounts/").respond(200, json={"results": []})
    r = health(client)
    assert r["ok"] is True
    assert r["endpoint"] == "health"
    assert r["payload"]["status"] == "ok"


@respx.mock
def test_health_fails_on_500(client):
    respx.get("http://test/api/v1/accounts/").respond(500, json={"error": "boom"})
    r = health(client)
    assert r["ok"] is False
    assert "HTTP 500" in r["error"]


@respx.mock
def test_list_accounts(client):
    respx.get("http://test/api/v1/accounts/").respond(200, json={
        "results": [{"id": 1, "name": "Caixa", "balance": "100.00", "account_type": "CHECKING"}]
    })
    r = list_accounts(client)
    assert r["ok"] is True
    assert r["endpoint"] == "accounts"
    assert r["payload"]["results"][0]["name"] == "Caixa"


@respx.mock
def test_list_accounts_error(client):
    respx.get("http://test/api/v1/accounts/").respond(401, json={"detail": "bad token"})
    r = list_accounts(client)
    assert r["ok"] is False
    assert "Token" in r["error"]