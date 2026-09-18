"""Account-related MCP tools."""
from ..helpers import _result, _safe_call


def list_accounts(client) -> dict:
    """List all accounts with current balances."""
    return _safe_call(lambda: _result(
        "accounts",
        client.request("GET", "accounts/"),
    ))


def create_account(client, name, account_type, currency='BRL', opening_balance='0.00') -> dict:
    body = {'name': name, 'account_type': account_type, 'currency': currency,
            'opening_balance': str(opening_balance)}
    return _safe_call(lambda: _result('accounts', client.request('POST', 'accounts/', json=body), body))


def update_account(client, id, **changes) -> dict:
    body = {key: value for key, value in changes.items() if value is not None}
    return _safe_call(lambda: _result('accounts', client.request('PATCH', f'accounts/{id}/', json=body), body))


def adjust_account_balance(client, id, new_balance, adjustment_date, reason, client_id) -> dict:
    body = {'new_balance': str(new_balance), 'adjustment_date': adjustment_date,
            'reason': reason, 'client_id': client_id}
    return _safe_call(lambda: _result('accounts/adjustments', client.request('POST', f'accounts/{id}/adjustments/', json=body), body))


def register_account_tools(mcp, client):
    """Register account tools with MCP server."""

    @mcp.tool()
    def finanpy_list_accounts() -> dict:
        """Lista todas as contas com saldos atuais.

        Returns:
            {ok, endpoint, params, payload} onde payload.results é
            [{id, name, balance, account_type}, ...]
        """
        return list_accounts(client)

    @mcp.tool()
    def finanpy_create_account(name: str, account_type: str, currency: str = 'BRL', opening_balance: str = '0.00') -> dict:
        """Cria uma conta, incluindo reserva (`savings`) com saldo de abertura."""
        return create_account(client, name, account_type, currency, opening_balance)

    @mcp.tool()
    def finanpy_update_account(id: int, name: str | None = None, account_type: str | None = None, currency: str | None = None, is_active: bool | None = None) -> dict:
        """Edita metadados de conta; saldo só pode mudar por ajuste auditável."""
        return update_account(client, id, name=name, account_type=account_type, currency=currency, is_active=is_active)

    @mcp.tool()
    def finanpy_adjust_account_balance(id: int, new_balance: str, adjustment_date: str, reason: str, client_id: str) -> dict:
        """Ajusta saldo de reserva/investimento com histórico auditável."""
        return adjust_account_balance(client, id, new_balance, adjustment_date, reason, client_id)
