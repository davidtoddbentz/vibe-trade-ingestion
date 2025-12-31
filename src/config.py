"""Configuration management."""

import json
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class SystemConfig:
    """System configuration from environment variables or CDP API key file."""

    coinbase_api_key: str
    coinbase_api_secret: str
    coinbase_environment: str = "live"

    @classmethod
    def from_env(cls) -> "SystemConfig":
        """Load configuration from CDP API key file.

        Requires a CDP API key JSON file. Fails immediately if not found or invalid.
        """
        # Try to load from CDP API key file
        cdp_key_file = os.getenv("COINBASE_CDP_KEY_FILE", "")

        # If not specified, look for cdp_api_key-*.json files in current directory
        if not cdp_key_file:
            current_dir = Path.cwd()
            cdp_files = list(current_dir.glob("cdp_api_key-*.json"))
            if not cdp_files:
                raise ValueError(
                    f"CDP API key file not found.\n"
                    f"  - Looked for: cdp_api_key-*.json in {current_dir}\n"
                    f"  - Set COINBASE_CDP_KEY_FILE to specify the path to your CDP key file"
                )
            # Use the most recent one found
            cdp_key_file = str(sorted(cdp_files, key=lambda p: p.stat().st_mtime, reverse=True)[0])

        # Verify file exists
        if not Path(cdp_key_file).exists():
            raise ValueError(
                f"CDP API key file not found: {cdp_key_file}\n"
                f"  - Verify the file path is correct\n"
                f"  - Or set COINBASE_CDP_KEY_FILE to the correct path"
            )

        # Load and parse the JSON file
        try:
            with open(cdp_key_file) as f:
                cdp_data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Invalid JSON in CDP API key file {cdp_key_file}: {e}\n"
                f"  - Please verify the file is valid JSON"
            ) from e
        except Exception as e:
            raise ValueError(f"Failed to read CDP API key file {cdp_key_file}: {e}") from e

        # Extract API key name and private key from CDP format
        api_key_name = cdp_data.get("name", "")
        api_secret = cdp_data.get("privateKey", "")

        if not api_key_name:
            raise ValueError(
                f"Missing 'name' field in CDP API key file {cdp_key_file}\n"
                f"  - The file must contain a 'name' field with the API key name"
            )

        if not api_secret:
            raise ValueError(
                f"Missing 'privateKey' field in CDP API key file {cdp_key_file}\n"
                f"  - The file must contain a 'privateKey' field with the EC private key"
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
