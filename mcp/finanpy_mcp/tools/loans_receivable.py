"""Loans-receivable MCP tools."""
import uuid

from ..helpers import _filter_params, _result, _safe_call


def create_loan_receivable(client, counterparty, amount, origin_account, loan_date, description, expected_return_date=None, client_id=None):
    body = {'counterparty': counterparty, 'amount': str(amount), 'origin_account': origin_account,
            'loan_date': loan_date, 'description': description,
            'client_id': client_id or f'hermes-loan-{uuid.uuid4().hex}'}
    if expected_return_date is not None:
        body['expected_return_date'] = expected_return_date
    return _safe_call(lambda: _result('loans-receivable', client.request('POST', 'loans-receivable/', json=body), body))


def list_loans_receivable(client, status=None):
    params = _filter_params({'status': status})
    return _safe_call(lambda: _result('loans-receivable', client.request('GET', 'loans-receivable/', params=params or None), params))


def settle_loan_receivable(client, id, amount, target_account, settlement_date, description=None, client_id=None):
    body = {'amount': str(amount), 'target_account': target_account,
            'settlement_date': settlement_date,
            'client_id': client_id or f'hermes-settlement-{uuid.uuid4().hex}'}
    if description is not None:
        body['description'] = description
    return _safe_call(lambda: _result('loans-receivable/settle', client.request('POST', f'loans-receivable/{id}/settle/', json=body), body))


def write_off_loan_receivable(client, id, reason):
    body = {'reason': reason}
    return _safe_call(lambda: _result('loans-receivable/write-off', client.request('POST', f'loans-receivable/{id}/write-off/', json=body), body))


def register_loans_receivable_tools(mcp, client):
    @mcp.tool()
    def finanpy_create_loan_receivable(counterparty: str, amount: str, origin_account: int, loan_date: str, description: str, expected_return_date: str | None = None, client_id: str | None = None) -> dict:
        """Registra ativo a receber sem classificá-lo como despesa."""
        return create_loan_receivable(client, counterparty, amount, origin_account, loan_date, description, expected_return_date, client_id)

    @mcp.tool()
    def finanpy_list_loans_receivable(status: str | None = None) -> dict:
        """Lista valores a receber, opcionalmente por status."""
        return list_loans_receivable(client, status)

    @mcp.tool()
    def finanpy_settle_loan_receivable(id: int, amount: str, target_account: int, settlement_date: str, description: str | None = None, client_id: str | None = None) -> dict:
        """Liquida total ou parcialmente um valor a receber sem criar receita."""
        return settle_loan_receivable(client, id, amount, target_account, settlement_date, description, client_id)

    @mcp.tool()
    def finanpy_write_off_loan_receivable(id: int, reason: str) -> dict:
        """Baixa um valor a receber como perda, com motivo obrigatório."""
        return write_off_loan_receivable(client, id, reason)
