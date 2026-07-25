import httpx
import pytest
from finanpy_mcp.http_client import FinanPyClient, FinanPyMCPError


def _mock_transport(status_code, json_body):
    def handler(request):
        return httpx.Response(status_code, json=json_body)
    return httpx.MockTransport(handler)


def _client(transport):
    return FinanPyClient(
        base_url="http://127.0.0.1:8001/api/v1/",
        token="t" * 40,
        timeout=10.0,
        transport=transport,
    )


def test_request_sends_bearer_token():
    captured = {}

    def handler(request):
        captured["auth"] = request.headers.get("authorization")
        captured["accept"] = request.headers.get("accept")
        return httpx.Response(200, json={"ok": True})

    client = _client(httpx.MockTransport(handler))
    result = client.request("GET", "accounts/")
    assert result == {"ok": True}
    assert captured["auth"] == f"Token t{'t' * 39}"
    assert captured["accept"] == "application/json"


def test_request_400_raises_error():
    client = _client(_mock_transport(400, {"detail": "Bad request"}))
    with pytest.raises(FinanPyMCPError, match="rejeitou"):
        client.request("GET", "accounts/")


def test_request_401_raises_error():
    client = _client(_mock_transport(401, {"detail": "Invalid token"}))
    with pytest.raises(FinanPyMCPError, match="Token.*inválido"):
        client.request("GET", "accounts/")


def test_request_404_raises_error():
    client = _client(_mock_transport(404, {"detail": "Not found"}))
    with pytest.raises(FinanPyMCPError, match="não encontrado"):
        client.request("GET", "accounts/42/")


def test_request_500_raises_error():
    client = _client(_mock_transport(500, {"error": "Internal"}))
    with pytest.raises(FinanPyMCPError, match="HTTP 500"):
        client.request("GET", "accounts/")


def test_request_timeout():
    def handler(request):
        raise httpx.TimeoutException("timed out")
    client = _client(httpx.MockTransport(handler))
    with pytest.raises(FinanPyMCPError, match="Tempo esgotado"):
        client.request("GET", "accounts/")


def test_request_connection_error():
    def handler(request):
        raise httpx.ConnectError("conn refused")
    client = _client(httpx.MockTransport(handler))
    with pytest.raises(FinanPyMCPError, match="Falha de comunicação"):
        client.request("GET", "accounts/")


def test_request_non_json():
    def handler(request):
        return httpx.Response(200, content=b"not json", headers={"content-type": "text/plain"})
    client = _client(httpx.MockTransport(handler))
    with pytest.raises(FinanPyMCPError, match="não-JSON"):
        client.request("GET", "accounts/")


def test_post_sends_json_body():
    captured = {}

    def handler(request):
        captured["body"] = request.read()
        captured["content_type"] = request.headers.get("content-type")
        return httpx.Response(201, json={"id": 99})

    client = _client(httpx.MockTransport(handler))
    result = client.request("POST", "transactions/quick/", json={"amount": "50.00"})
    assert result == {"id": 99}
    assert b"50.00" in captured["body"]
    assert "application/json" in captured["content_type"]