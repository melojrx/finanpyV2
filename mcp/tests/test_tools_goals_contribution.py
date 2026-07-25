import json
import pytest
import respx
from finanpy_mcp.tools.goals import add_goal_contribution
from finanpy_mcp.http_client import FinanPyClient


@pytest.fixture
def client():
    return FinanPyClient(
        base_url="http://test/api/v1/",
        token="t" * 40,
        timeout=5.0,
    )


@respx.mock
def test_add_contribution_with_date(client):
    route = respx.post("http://test/api/v1/goal-contributions/")
    route.respond(201, json={"id": 50, "goal": 3, "amount": "100.00", "date": "2026-07-24"})
    r = add_goal_contribution(client, goal_id=3, amount="100.00", date="2026-07-24")
    assert r["ok"] is True
    body = json.loads(route.calls.last.request.content)
    assert body["goal"] == 3
    assert body["amount"] == "100.00"
    assert body["date"] == "2026-07-24"


@respx.mock
def test_add_contribution_default_date_today(client):
    route = respx.post("http://test/api/v1/goal-contributions/")
    route.respond(201, json={"id": 51, "goal": 3, "amount": "50.00"})
    r = add_goal_contribution(client, goal_id=3, amount="50.00")
    assert r["ok"] is True
    body = json.loads(route.calls.last.request.content)
    assert "date" in body
    # Should be today's date in YYYY-MM-DD
    assert len(body["date"]) == 10


@respx.mock
def test_add_contribution_empty_amount(client):
    r = add_goal_contribution(client, goal_id=3, amount="")
    assert r["ok"] is False
    assert "amount" in r["error"].lower()


@respx.mock
def test_add_contribution_api_error(client):
    respx.post("http://test/api/v1/goal-contributions/").respond(
        400, json={"goal": ["Meta não pertence ao usuário."]}
    )
    r = add_goal_contribution(client, goal_id=999, amount="100.00")
    assert r["ok"] is False
    assert "rejeitou" in r["error"]


@respx.mock
def test_add_contribution_goal_not_found(client):
    respx.post("http://test/api/v1/goal-contributions/").respond(404, json={"detail": "Not found"})
    r = add_goal_contribution(client, goal_id=0, amount="100.00")
    assert r["ok"] is False
    assert "não encontrado" in r["error"]