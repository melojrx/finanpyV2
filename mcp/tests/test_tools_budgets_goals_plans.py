import pytest
import respx
from finanpy_mcp.tools.budgets import list_budgets
from finanpy_mcp.tools.goals import list_goals
from finanpy_mcp.tools.plans import get_monthly_plan
from finanpy_mcp.http_client import FinanPyClient


@pytest.fixture
def client():
    return FinanPyClient(
        base_url="http://test/api/v1/",
        token="t" * 40,
        timeout=5.0,
    )


@respx.mock
def test_list_budgets_no_filters(client):
    respx.get("http://test/api/v1/budgets/").respond(200, json={
        "results": [{"id": 1, "name": "Alimentação", "planned_amount": "500.00"}]
    })
    r = list_budgets(client)
    assert r["ok"] is True
    assert r["params"] == {}
    assert r["payload"]["results"][0]["name"] == "Alimentação"


@respx.mock
def test_list_budgets_with_filters(client):
    route = respx.get("http://test/api/v1/budgets/")
    route.respond(200, json={"results": []})
    r = list_budgets(client, year=2026, month=7, active=True)
    assert r["ok"] is True
    assert r["params"] == {"year": 2026, "month": 7, "active": "true"}
    sent = route.calls.last.request.url.params
    assert sent["year"] == "2026"
    assert sent["month"] == "7"
    assert sent["active"] == "true"


@respx.mock
def test_list_goals_no_status(client):
    respx.get("http://test/api/v1/goals/").respond(200, json={
        "results": [{"id": 1, "name": "Viagem", "target_amount": "10000.00", "status": "ACTIVE"}]
    })
    r = list_goals(client)
    assert r["ok"] is True
    assert r["params"] == {}
    assert r["payload"]["results"][0]["name"] == "Viagem"


@respx.mock
def test_list_goals_with_status(client):
    route = respx.get("http://test/api/v1/goals/")
    route.respond(200, json={"results": []})
    r = list_goals(client, status="ACTIVE")
    assert r["ok"] is True
    assert r["params"] == {"status": "ACTIVE"}
    assert route.calls.last.request.url.params["status"] == "ACTIVE"


@respx.mock
def test_get_monthly_plan(client):
    respx.get("http://test/api/v1/monthly-plans/").respond(200, json={
        "results": [{"id": 42, "year": 2026, "month": 7, "status": "ACTIVE", "renda_prevista": "5000.00"}]
    })
    r = get_monthly_plan(client, year=2026, month=7)
    assert r["ok"] is True
    assert r["params"] == {"year": 2026, "month": 7}
    assert r["payload"]["results"][0]["id"] == 42


@respx.mock
def test_get_monthly_plan_empty(client):
    respx.get("http://test/api/v1/monthly-plans/").respond(200, json={"results": []})
    r = get_monthly_plan(client, year=2026, month=7)
    assert r["ok"] is True
    assert r["payload"]["results"] == []


@respx.mock
def test_budgets_error(client):
    respx.get("http://test/api/v1/budgets/").respond(401, json={"detail": "bad"})
    r = list_budgets(client)
    assert r["ok"] is False
    assert "Token" in r["error"]