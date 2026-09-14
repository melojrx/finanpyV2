"""Helpers for reading production settings from environment or mounted files."""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured


def env_secret(name, default=None, required=False):
    """Read ``NAME_FILE`` first, falling back to ``NAME``."""
    file_name = os.getenv(f"{name}_FILE")
    if file_name:
        try:
            value = Path(file_name).read_text(encoding="utf-8").strip()
        except OSError as exc:
            raise ImproperlyConfigured(f"Unable to read {name}_FILE") from exc
    else:
        value = os.getenv(name, default)

    if required and not value:
        raise ImproperlyConfigured(f"Missing required environment variable: {name}")
    return value
