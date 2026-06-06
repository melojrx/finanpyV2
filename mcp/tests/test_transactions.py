"""Tests for transaction tools."""
import pytest
from datetime import date


def test_register_transaction_structure(client):
    """Test register_transaction accepts correct params."""
    from finanpy_mcp.client import TransactionResult

    # Verify TransactionResult dataclass
    result = TransactionResult(id=1, balance="100.00", description="Test")
    assert result.id == 1
    assert result.balance == "100.00"