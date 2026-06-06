"""Tests for category tools."""
import pytest


def test_get_categories_returns_list(client):
    """Test get_categories returns list."""
    from finanpy_mcp.client import FinanPyClient

    categories = client.get_categories()
    assert isinstance(categories, list)