"""Configuration management."""

import os
from dataclasses import dataclass


@dataclass
class SystemConfig:
    """System configuration from environment variables."""

    coinbase_api_key: str
    coinbase_api_secret: str
    coinbase_environment: str = "live"

    @classmethod
    def from_env(cls) -> "SystemConfig":
        """Load configuration from CDP API credentials via environment variables.

        Requires:
        - COINBASE_CDP_KEY_NAME: API key name
        - COINBASE_CDP_KEY_SECRET: Private key
        """
        api_key_name = os.getenv("COINBASE_CDP_KEY_NAME", "")
        api_secret = os.getenv("COINBASE_CDP_KEY_SECRET", "")

        if not api_key_name:
            raise ValueError(
                "COINBASE_CDP_KEY_NAME environment variable is required\n"
                "  - Set it to your Coinbase CDP API key name"
            )

        if not api_secret:
            raise ValueError(
                "COINBASE_CDP_KEY_SECRET environment variable is required\n"
                "  - Set it to your Coinbase CDP private key"
            )

        # For CDP, we can use either the full name or just the key ID
        # Check if user wants to use full name (default: use key ID)
        use_full_name = os.getenv("COINBASE_USE_FULL_API_KEY_NAME", "false").lower() == "true"

        if use_full_name:
            # Use the full API key name path
            api_key = api_key_name
        else:
            # Extract just the key ID from the full path if it's a CDP format
            # Format: organizations/.../apiKeys/{key_id}
            if "/apiKeys/" in api_key_name:
                api_key = api_key_name.split("/apiKeys/")[-1]
            else:
                api_key = api_key_name

        environment = os.getenv("COINBASE_ENVIRONMENT", "live")

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
