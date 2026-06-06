"""Test fixtures for MCP FinanPy."""
import pytest
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from finanpy_mcp.config import Config
from finanpy_mcp.client import FinanPyClient


@pytest.fixture
def config():
    """Test config with SQLite."""
    return Config(
        token="test_token",
        use_sqlite=True,
        db_path=Path(__file__).parent.parent.parent / "db.sqlite3",
    )


@pytest.fixture
def client(config):
    """Test client."""
    return FinanPyClient(config)