"""Shared helpers for MCP tools."""
from typing import Any, Callable

from .http_client import FinanPyMCPError
from .sanitization import sanitize_payload


def _result(endpoint: str, payload: Any, params: dict | None = None) -> dict:
    """Build a standardized success response."""
    return {
        "ok": True,
        "endpoint": endpoint,
        "params": sanitize_payload(params or {}),
        "payload": sanitize_payload(payload),
    }


def _filter_params(d: dict) -> dict:
    """Remove keys with None values, preserving 0 and False."""
    return {k: v for k, v in d.items() if v is not None}


def _safe_call(fn: Callable) -> dict:
    """Execute fn, catching FinanPyMCPError and returning a dict in either case."""
    try:
        return fn()
    except FinanPyMCPError as e:
        return {"ok": False, "error": str(e)}


def _clean_text(value: str, *, max_len: int = 120) -> str:
    return str(value or "").strip()[:max_len]


def _safe_int(value, *, default: int, min_value: int, max_value: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(min_value, min(max_value, parsed))