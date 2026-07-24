"""Sanitization of secrets in payloads returned to the agent."""
import re
from typing import Any

_SECRET_KEY_RE = re.compile(
    r"(token|secret|password|authorization|api[_-]?key|bearer|cookie|session)",
    re.I,
)


def _mask_value(key: str, value: Any) -> Any:
    if value is None:
        return None
    if _SECRET_KEY_RE.search(key):
        return "***redacted***"
    return value


def sanitize_payload(value: Any, *, key: str = "") -> Any:
    """Recursively redact secret-like keys from a payload."""
    masked = _mask_value(key, value) if key else value
    if masked != value:
        return masked

    if isinstance(value, dict):
        return {str(k): sanitize_payload(v, key=str(k)) for k, v in value.items()}
    if isinstance(value, list):
        return [sanitize_payload(item, key=key) for item in value]
    return value