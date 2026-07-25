import pytest
import respx
from finanpy_mcp.tools.reports import dashboard_snapshot, monthly_summary, yearly_summary
from finanpy_mcp.http_client import FinanPyClient


@pytest.fixture
def client():
    return FinanPyClient(
        base_url="http://test/api/v1/",
        token="t" * 40,
        timeout=5.0,
    )


@respx.mock
def test_dashboard_snapshot_default(client):
    respx.get("http://test/api/v1/dashboard/snapshot/").respond(200, json={
        "totals": {"total_balance": "1000.00"},
        "recent_transactions": [],
    })
    r = dashboard_snapshot(client)
    assert r["ok"] is True
    assert r["payload"]["totals"]["total_balance"] == "1000.00"
    assert r["params"] == {}


@respx.mock
def test_dashboard_snapshot_with_include(client):
    route = respx.get("http://test/api/v1/dashboard/snapshot/")
    route.respond(200, json={"totals": {}, "budgets": [], "goals": [], "chart_6m": {}})
    r = dashboard_snapshot(client, include="budgets,goals,chart_6m")
    assert r["ok"] is True
    assert r["params"]["include"] == "budgets,goals,chart_6m"
    sent = route.calls.last.request.url.params
    assert sent["include"] == "budgets,goals,chart_6m"


@respx.mock
def test_dashboard_snapshot_error(client):
    respx.get("http://test/api/v1/dashboard/snapshot/").respond(404, json={"detail": "nope"})
    r = dashboard_snapshot(client)
    assert r["ok"] is False
    assert "não encontrado" in r["error"]


@respx.mock
def test_monthly_summary(client):
    respx.get("http://test/api/v1/summary/monthly/").respond(200, json={
        "year": 2026, "month": 7, "income": "5000.00",
        "expenses": "3000.00", "balance": "2000.00", "transaction_count": 25
    })
    r = monthly_summary(client, year=2026, month=7)
    assert r["ok"] is True
    assert r["payload"]["balance"] == "2000.00"
    assert r["params"] == {"year": 2026, "month": 7}


@respx.mock
def test_yearly_summary(client):
    respx.get("http://test/api/v1/summary/yearly/").respond(200, json={
        "year": 2026, "total_income": "60000.00",
        "total_expenses": "36000.00", "months": []
    })
    r = yearly_summary(client, year=2026)
    assert r["ok"] is True
    assert r["params"] == {"year": 2026}
    assert r["payload"]["total_income"] == "60000.00"