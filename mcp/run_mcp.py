#!/usr/bin/env python3
"""MCP FinanPy Server entry point."""
from finanpy_mcp.server import main
import asyncio

if __name__ == "__main__":
    asyncio.run(main())