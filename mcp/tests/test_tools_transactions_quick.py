import json
import re
import pytest
import respx
from finanpy_mcp.tools.transactions import register_quick_transaction
from finanpy_mcp.http_client import FinanPyClient


@pytest.fixture
def client():
    return FinanPyClient(
        base_url="http://test/api/v1/",
        token="t" * 40,
        timeout=5.0,
    )


@respx.mock
def test_quick_transaction_generates_client_id(client):
    route = respx.post("http://test/api/v1/transactions/quick/")
    route.respond(201, json={"id": 99, "amount": "50.00"})
    r = register_quick_transaction(
        client, amount="50.00", transaction_type="EXPENSE",
        account=1, category=2,
    )
    assert r["ok"] is True
    body = json.loads(route.calls.last.request.content)
    assert "client_id" in body
    assert body["client_id"].startswith("hermes-")
    assert len(body["client_id"]) > 10
    assert body["amount"] == "50.00"
    assert body["transaction_type"] == "EXPENSE"
    assert body["account"] == 1
    assert body["category"] == 2


@respx.mock
def test_quick_transaction_with_explicit_client_id(client):
    route = respx.post("http://test/api/v1/transactions/quick/")
    route.respond(201, json={"id": 100})
    r = register_quick_transaction(
        client, amount="10.00", transaction_type="INCOME",
        account=1, category=3, client_id="my-custom-id",
    )
    assert r["ok"] is True
    body = json.loads(route.calls.last.request.content)
    assert body["client_id"] == "my-custom-id"


@respx.mock
def test_quick_transaction_with_description_and_date(client):
    route = respx.post("http://test/api/v1/transactions/quick/")
    route.respond(201, json={"id": 101})
    r = register_quick_transaction(
        client, amount="25.50", transaction_type="EXPENSE",
        account=1, category=2,
        description="Almoço", transaction_date="2026-07-24",
        notes="pago em dinheiro",
    )
    assert r["ok"] is True
    body = json.loads(route.calls.last.request.content)
    assert body["description"] == "Almoço"
    assert body["transaction_date"] == "2026-07-24"
    assert body["notes"] == "pago em dinheiro"
    assert "client_id" in body  # still auto-generated


@respx.mock
def test_quick_transaction_invalid_type(client):
    r = register_quick_transaction(
        client, amount="10.00", transaction_type="INVALID",
        account=1, category=2,
    )
    assert r["ok"] is False
    assert "transaction_type" in r["error"]


@respx.mock
def test_quick_transaction_empty_amount(client):
    r = register_quick_transaction(
        client, amount="", transaction_type="EXPENSE",
        account=1, category=2,
    )
    assert r["ok"] is False
    assert "amount" in r["error"].lower()


@respx.mock
def test_quick_transaction_api_error(client):
    respx.post("http://test/api/v1/transactions/quick/").respond(
        400, json={"amount": ["A valid number is required."]}
    )
    r = register_quick_transaction(
        client, amount="abc", transaction_type="EXPENSE",
        account=1, category=2,
    )
    assert r["ok"] is False
    assert "rejeitou" in r["error"]


@respx.mock
def test_quick_transaction_idempotent_response(client):
    route = respx.post("http://test/api/v1/transactions/quick/")
    route.respond(200, json={"id": 99, "amount": "50.00"})
    r = register_quick_transaction(
        client, amount="50.00", transaction_type="EXPENSE",
        account=1, category=2, client_id="dup-123",
    )
    assert r["ok"] is True
    assert r["payload"]["id"] == 99