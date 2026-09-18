"""Transfer-related MCP tools."""
import uuid

from ..helpers import _filter_params, _result, _safe_call


def create_transfer(client, source_account, target_account, amount, transfer_date,
                    description=None, destination_context=None, client_id=None):
    body = {
        'source_account': source_account, 'target_account': target_account,
        'amount': str(amount), 'transfer_date': transfer_date,
        'client_id': client_id or f'hermes-transfer-{uuid.uuid4().hex}',
    }
    if description is not None:
        body['description'] = description
    if destination_context is not None:
        body['destination_context'] = destination_context
    return _safe_call(lambda: _result('transfers', client.request('POST', 'transfers/', json=body), body))


def list_transfers(client, account=None, date_from=None, date_to=None):
    params = _filter_params({'account': account, 'date_from': date_from, 'date_to': date_to})
    return _safe_call(lambda: _result('transfers', client.request('GET', 'transfers/', params=params or None), params))


def register_transfer_tools(mcp, client):
    @mcp.tool()
    def finanpy_create_transfer(source_account: int, target_account: int, amount: str, transfer_date: str, description: str | None = None, destination_context: str | None = None, client_id: str | None = None) -> dict:
        """Move saldo entre contas sem criar receita ou despesa."""
        return create_transfer(client, source_account, target_account, amount, transfer_date, description, destination_context, client_id)

    @mcp.tool()
    def finanpy_list_transfers(account: int | None = None, date_from: str | None = None, date_to: str | None = None) -> dict:
        """Lista transferências por conta e período."""
        return list_transfers(client, account, date_from, date_to)
