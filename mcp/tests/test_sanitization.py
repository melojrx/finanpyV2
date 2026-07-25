from finanpy_mcp.sanitization import sanitize_payload


def test_redacts_token_key():
    payload = {"token": "abc123", "name": "João"}
    result = sanitize_payload(payload)
    assert result["token"] == "***redacted***"
    assert result["name"] == "João"


def test_redacts_authorization():
    payload = {"Authorization": "Bearer xyz", "data": [1, 2]}
    result = sanitize_payload(payload)
    assert result["Authorization"] == "***redacted***"
    assert result["data"] == [1, 2]


def test_redacts_nested():
    payload = {
        "outer": {"api_key": "secret", "normal": "ok"},
        "list": [{"password": "p", "id": 1}],
    }
    result = sanitize_payload(payload)
    assert result["outer"]["api_key"] == "***redacted***"
    assert result["outer"]["normal"] == "ok"
    assert result["list"][0]["password"] == "***redacted***"
    assert result["list"][0]["id"] == 1


def test_redacts_case_insensitive():
    payload = {"API_Key": "secret", "SECRET": "s"}
    result = sanitize_payload(payload)
    assert result["API_Key"] == "***redacted***"
    assert result["SECRET"] == "***redacted***"


def test_preserves_none():
    payload = {"token": None, "name": "x"}
    result = sanitize_payload(payload)
    assert result["token"] is None


def test_handles_plain_string():
    assert sanitize_payload("hello") == "hello"
    assert sanitize_payload(42) == 42
    assert sanitize_payload([]) == []