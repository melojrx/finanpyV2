import os

from finanpy_mcp.config import Config


def test_config_from_env_success(monkeypatch):
    monkeypatch.setenv("FINANPY_API_BASE_URL", "http://127.0.0.1:8001/api/v1/")
    monkeypatch.setenv("FINANPY_API_TOKEN", "a" * 40)
    cfg = Config.from_env()
    assert cfg.base_url == "http://127.0.0.1:8001/api/v1/"
    assert cfg.token == "a" * 40
    assert cfg.timeout_seconds == 20.0


def test_config_missing_base_url(monkeypatch):
    monkeypatch.delenv("FINANPY_API_BASE_URL", raising=False)
    monkeypatch.setenv("FINANPY_API_TOKEN", "a" * 40)
    try:
        Config.from_env()
        assert False, "Should have raised"
    except ValueError as e:
        assert "FINANPY_API_BASE_URL" in str(e)


def test_config_base_url_without_trailing_slash(monkeypatch):
    monkeypatch.setenv("FINANPY_API_BASE_URL", "http://127.0.0.1:8001/api/v1")
    monkeypatch.setenv("FINANPY_API_TOKEN", "a" * 40)
    try:
        Config.from_env()
        assert False, "Should have raised"
    except ValueError as e:
        assert "/api/v1" in str(e)


def test_config_token_too_short(monkeypatch):
    monkeypatch.setenv("FINANPY_API_BASE_URL", "http://127.0.0.1:8001/api/v1/")
    monkeypatch.setenv("FINANPY_API_TOKEN", "short")
    try:
        Config.from_env()
        assert False, "Should have raised"
    except ValueError as e:
        assert "FINANPY_API_TOKEN" in str(e)


def test_config_custom_timeout(monkeypatch):
    monkeypatch.setenv("FINANPY_API_BASE_URL", "http://127.0.0.1:8001/api/v1/")
    monkeypatch.setenv("FINANPY_API_TOKEN", "a" * 40)
    monkeypatch.setenv("FINANPY_API_TIMEOUT_SECONDS", "30")
    cfg = Config.from_env()
    assert cfg.timeout_seconds == 30.0