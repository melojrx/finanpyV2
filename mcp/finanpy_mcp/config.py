"""Configuration loading from environment variables."""
import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv(override=False)


@dataclass
class Config:
    """FinanPy MCP configuration."""

    base_url: str
    token: str
    timeout_seconds: float = 20.0

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        base_url = os.getenv("FINANPY_API_BASE_URL", "").strip()
        if not base_url:
            raise ValueError(
                "FINANPY_API_BASE_URL é obrigatório "
                "(ex.: http://127.0.0.1:8001/api/v1/)"
            )
        if not base_url.endswith("/api/v1/"):
            raise ValueError(
                "FINANPY_API_BASE_URL deve terminar com /api/v1/ "
                f"(recebido: {base_url})"
            )

        token = os.getenv("FINANPY_API_TOKEN", "").strip()
        if len(token) < 20:
            raise ValueError(
                "FINANPY_API_TOKEN é obrigatório e deve ter pelo menos "
                "20 caracteres."
            )

        timeout_str = os.getenv("FINANPY_API_TIMEOUT_SECONDS", "20")
        try:
            timeout_seconds = float(timeout_str)
        except ValueError:
            timeout_seconds = 20.0

        return cls(
            base_url=base_url,
            token=token,
            timeout_seconds=timeout_seconds,
        )


def get_config() -> Config:
    """Get MCP configuration."""
    return Config.from_env()