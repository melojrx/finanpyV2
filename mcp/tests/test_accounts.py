"""Tests for account tools."""
import pytest
from finanpy_mcp.client import FinanPyClient
from finanpy_mcp.tools.accounts import get_accounts


def test_get_accounts(client):
    """Test get_accounts returns list."""
    accounts = get_accounts(client)
    assert isinstance(accounts, list)
    if accounts:
        assert "id" in accounts[0]
        assert "name" in accounts[0]
        assert "balance" in accounts[0]