import json

import respx

from finanpy_mcp.http_client import FinanPyClient
from finanpy_mcp.tools.accounts import adjust_account_balance
from finanpy_mcp.tools.loans_receivable import create_loan_receivable
from finanpy_mcp.tools.transfers import create_transfer


def make_client():
    return FinanPyClient(base_url='http://test/api/v1/', token='t' * 40)


@respx.mock
def test_create_transfer_uses_public_endpoint_and_hermes_user_agent():
    route = respx.post('http://test/api/v1/transfers/').respond(201, json={'id': 1})
    result = create_transfer(make_client(), 1, 2, '49.90', '2026-09-18', client_id='transfer-1')

    assert result['ok'] is True
    assert json.loads(route.calls.last.request.content)['source_account'] == 1
    assert route.calls.last.request.headers['User-Agent'] == 'Hermes/FinanPyMCP 1.1'


@respx.mock
def test_adjustment_posts_auditable_payload():
    route = respx.post('http://test/api/v1/accounts/2/adjustments/').respond(201, json={'id': 2})
    result = adjust_account_balance(make_client(), 2, '100.00', '2026-09-18', 'Rendimento', 'adjust-1')

    assert result['ok'] is True
    assert json.loads(route.calls.last.request.content)['reason'] == 'Rendimento'


@respx.mock
def test_loan_creation_posts_to_receivables_without_transaction_endpoint():
    route = respx.post('http://test/api/v1/loans-receivable/').respond(201, json={'id': 3})
    result = create_loan_receivable(make_client(), 'Sabrina', '600.00', 2, '2026-09-18', 'Brabus', client_id='loan-1')

    assert result['ok'] is True
    assert json.loads(route.calls.last.request.content)['amount'] == '600.00'
