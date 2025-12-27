"""Configuration management."""

import os
from dataclasses import dataclass


@dataclass
class SystemConfig:
    """System configuration from environment variables."""

    coinbase_api_key: str
    coinbase_api_secret: str
    coinbase_environment: str = "sandbox"

    @classmethod
    def from_env(cls) -> "SystemConfig":
        """Load configuration from environment variables."""
        api_key = os.getenv("COINBASE_API_KEY", "").strip()
        api_secret = os.getenv("COINBASE_API_SECRET", "").strip()
        environment = os.getenv("COINBASE_ENVIRONMENT", "sandbox")

        if not api_key or not api_secret:
            # Provide helpful error message
            missing = []
            if not api_key:
                missing.append("COINBASE_API_KEY")
            if not api_secret:
                missing.append("COINBASE_API_SECRET")
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing)}\n"
                f"Please set these in your .env file or export them as environment variables.\n"
                f"Current values: COINBASE_API_KEY={'SET' if api_key else 'EMPTY/MISSING'}, "
                f"COINBASE_API_SECRET={'SET' if api_secret else 'EMPTY/MISSING'}"
            )

        return cls(
            coinbase_api_key=api_key,
            coinbase_api_secret=api_secret,
            coinbase_environment=environment,
        )

    def validate(self) -> None:
        """Validate configuration."""
        if not self.coinbase_api_key:
            raise ValueError("COINBASE_API_KEY is required")
        if not self.coinbase_api_secret:
            raise ValueError("COINBASE_API_SECRET is required")
        if self.coinbase_environment not in ["sandbox", "live"]:
            raise ValueError("COINBASE_ENVIRONMENT must be 'sandbox' or 'live'")


@dataclass
class IngestionConfig:
    """ClickHouse configuration from environment variables."""

    clickhouse_host: str
    clickhouse_port: int
    clickhouse_user: str
    clickhouse_password: str
    clickhouse_database: str

    def __init__(self):
        """Load configuration from environment variables."""
        self.clickhouse_host = os.getenv("CLICKHOUSE_HOST", "localhost")
        self.clickhouse_port = int(os.getenv("CLICKHOUSE_PORT", "8123"))
        # Support both CLICKHOUSE_USERNAME and CLICKHOUSE_USER for backward compatibility
        self.clickhouse_user = os.getenv("CLICKHOUSE_USERNAME") or os.getenv("CLICKHOUSE_USER", "default")
        self.clickhouse_password = os.getenv("CLICKHOUSE_PASSWORD", "")
        # Support both CLICKHOUSE_DATABASE and CLICKHOUSE_DB for backward compatibility
        self.clickhouse_database = os.getenv("CLICKHOUSE_DATABASE") or os.getenv("CLICKHOUSE_DB", "default")

