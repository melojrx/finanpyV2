#!/usr/bin/env python3
"""Smoke test — runs post-deploy to verify MCP can reach the FinanPy API.

Exit 0 = all good. Exit 1 = something broke.
"""
import sys

from .config import get_config
from .http_client import FinanPyClient
from .tools.health import health
from .tools.reports import dashboard_snapshot


def main():
    try:
        cfg = get_config()
    except ValueError as e:
        print(f"FAIL: config error: {e}", file=sys.stderr)
        return 1

    client = FinanPyClient(
        base_url=cfg.base_url,
        token=cfg.token,
        timeout=cfg.timeout_seconds,
    )

    print("Testing health...")
    r = health(client)
    if r.get("ok"):
        print(f"  OK: {r['payload']}")
    else:
        print(f"  FAIL: {r.get('error')}", file=sys.stderr)
        return 1

    print("Testing dashboard_snapshot...")
    r = dashboard_snapshot(client)
    if r.get("ok"):
        print(f"  OK: {r['payload'].get('totals', {})}")
    else:
        print(f"  FAIL: {r.get('error')}", file=sys.stderr)
        return 1

    print("All smoke tests passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())