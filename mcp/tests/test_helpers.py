import pytest
from finanpy_mcp.helpers import _result, _filter_params, _safe_call, _clean_text, _safe_int
from finanpy_mcp.http_client import FinanPyMCPError


def test_result_basic():
    r = _result("accounts", {"id": 1})
    assert r == {"ok": True, "endpoint": "accounts", "params": {}, "payload": {"id": 1}}


def test_result_with_params():
    r = _result("accounts", {"id": 1}, params={"type": "INCOME"})
    assert r["params"] == {"type": "INCOME"}


def test_filter_params_removes_none():
    out = _filter_params({"a": 1, "b": None, "c": "x", "d": 0})
    assert out == {"a": 1, "c": "x", "d": 0}


def test_filter_params_empty():
    assert _filter_params({"a": None}) == {}


def test_safe_call_success():
    def fn():
        return {"ok": True}
    assert _safe_call(fn) == {"ok": True}


def test_safe_call_catches_error():
    def fn():
        raise FinanPyMCPError("Boom")
    r = _safe_call(fn)
    assert r["ok"] is False
    assert "Boom" in r["error"]


def test_clean_text_strips_and_truncates():
    assert _clean_text("  hello  ") == "hello"
    assert _clean_text("x" * 200, max_len=10) == "xxxxxxxxxx"


def test_safe_int():
    assert _safe_int(5, default=1, min_value=1, max_value=100) == 5
    assert _safe_int("abc", default=10, min_value=1, max_value=100) == 10
    assert _safe_int(0, default=1, min_value=1, max_value=100) == 1
    assert _safe_int(999, default=1, min_value=1, max_value=100) == 100