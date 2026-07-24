import pytest
import respx
from finanpy_mcp.tools.transactions import confirm_pending_transaction
from finanpy_mcp.http_client import FinanPyClient


@pytest.fixture
def client():
    return FinanPyClient(
        base_url="http://test/api/v1/",
        token="t" * 40,
        timeout=5.0,
    )


@respx.mock
def test_confirm_pending_success(client):
    respx.post("http://test/api/v1/transactions/42/confirm/").respond(
        200, json={"id": 42, "status": "CONFIRMED"}
    )
    r = confirm_pending_transaction(client, id=42)
    assert r["ok"] is True
    assert r["params"] == {"id": 42}
    assert r["payload"]["status"] == "CONFIRMED"


@respx.mock
def test_confirm_pending_already_confirmed(client):
    respx.post("http://test/api/v1/transactions/42/confirm/").respond(
        400, json={"detail": "Apenas transações pendentes podem ser efetivadas."}
    )
    r = confirm_pending_transaction(client, id=42)
    assert r["ok"] is False
    assert "rejeitou" in r["error"]


@respx.mock
def test_confirm_pending_not_found(client):
    respx.post("http://test/api/v1/transactions/999/confirm/").respond(
        404, json={"detail": "Not found"}
    )
    r = confirm_pending_transaction(client, id=999)
    assert r["ok"] is False
    assert "não encontrado" in r["error"]


@respx.mock
def test_confirm_pending_server_error(client):
    respx.post("http://test/api/v1/transactions/1/confirm/").respond(500, json={"error": "boom"})
    r = confirm_pending_transaction(client, id=1)
    assert r["ok"] is False
    assert "HTTP 500" in r["error"]