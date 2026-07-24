import pytest
import respx
from finanpy_mcp.tools.transactions import list_transactions
from finanpy_mcp.http_client import FinanPyClient


@pytest.fixture
def client():
    return FinanPyClient(
        base_url="http://test/api/v1/",
        token="t" * 40,
        timeout=5.0,
    )


@respx.mock
def test_list_transactions_no_filters(client):
    respx.get("http://test/api/v1/transactions/").respond(200, json={
        "count": 1,
        "results": [{"id": 10, "amount": "50.00", "transaction_type": "EXPENSE"}]
    })
    r = list_transactions(client)
    assert r["ok"] is True
    assert r["params"] == {"page": 1, "page_size": 50}
    assert r["payload"]["results"][0]["id"] == 10


@respx.mock
def test_list_transactions_with_filters(client):
    route = respx.get("http://test/api/v1/transactions/")
    route.respond(200, json={"count": 0, "results": []})
    r = list_transactions(client, year=2026, month=7, transaction_type="EXPENSE", page=2, page_size=10)
    assert r["ok"] is True
    sent_params = route.calls.last.request.url.params
    assert sent_params["year"] == "2026"
    assert sent_params["month"] == "7"
    assert sent_params["type"] == "EXPENSE"
    assert sent_params["page"] == "2"
    assert sent_params["page_size"] == "10"


@respx.mock
def test_list_transactions_error(client):
    respx.get("http://test/api/v1/transactions/").respond(500, json={"error": "boom"})
    r = list_transactions(client)
    assert r["ok"] is False
    assert "HTTP 500" in r["error"]


@respx.mock
def test_list_transactions_sanitizes_in_response(client):
    respx.get("http://test/api/v1/transactions/").respond(200, json={
        "results": [{"id": 1, "token": "secret-value", "amount": "10"}]
    })
    r = list_transactions(client)
    assert r["payload"]["results"][0]["token"] == "***redacted***"
    assert r["payload"]["results"][0]["amount"] == "10"