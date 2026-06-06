"""Configuration loading from environment variables."""
import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    """FinanPy MCP configuration."""

    token: str
    use_sqlite: bool
    db_path: Path | None = None
    db_host: str | None = None
    db_port: int = 5432
    db_name: str | None = None
    db_user: str | None = None
    db_password: str | None = None

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        use_sqlite = os.getenv("FINANFY_USE_SQLITE", "true").lower() == "true"

        if use_sqlite:
            db_path = os.getenv("FINANFY_DB_PATH")
            if not db_path:
                raise ValueError("FINANFY_DB_PATH required when FINANFY_USE_SQLITE=true")
            return cls(
                token=os.getenv("FINANFY_TOKEN", ""),
                use_sqlite=True,
                db_path=Path(db_path),
            )
        else:
            return cls(
                token=os.getenv("FINANFY_TOKEN", ""),
                use_sqlite=False,
                db_host=os.getenv("FINANFY_DB_HOST", "127.0.0.1"),
                db_port=int(os.getenv("FINANFY_DB_PORT", "5432")),
                db_name=os.getenv("FINANFY_DB_NAME", "finanpy"),
                db_user=os.getenv("FINANFY_DB_USER", "finanpy"),
                db_password=os.getenv("FINANFY_DB_PASSWORD", ""),
            )


def get_config() -> Config:
    """Get MCP configuration."""
    return Config.from_env()