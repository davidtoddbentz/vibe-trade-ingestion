"""ClickHouse client and connection management."""

import logging
import os
from typing import Optional

import clickhouse_connect

logger = logging.getLogger(__name__)


class ClickHouseClient:
    """ClickHouse client for data ingestion.

    Automatically uses environment variables for configuration.
    """

    _client: Optional[clickhouse_connect.driver.Client] = None

    @classmethod
    def get_client(cls) -> clickhouse_connect.driver.Client:
        """Get or create ClickHouse client.

        Reads configuration from environment variables:
        - CLICKHOUSE_HOST (default: localhost)
        - CLICKHOUSE_PORT (default: 8123)
        - CLICKHOUSE_USERNAME or CLICKHOUSE_USER (default: default)
        - CLICKHOUSE_PASSWORD (optional)
        - CLICKHOUSE_DATABASE or CLICKHOUSE_DB (default: default)
        """
        if cls._client is None:
            host = os.getenv("CLICKHOUSE_HOST", "localhost")
            port = int(os.getenv("CLICKHOUSE_PORT", "8123"))
            # Support both variable names for backward compatibility
            username = os.getenv("CLICKHOUSE_USERNAME") or os.getenv("CLICKHOUSE_USER", "default")
            password = os.getenv("CLICKHOUSE_PASSWORD", "")
            # Support both variable names for backward compatibility
            database = os.getenv("CLICKHOUSE_DATABASE") or os.getenv("CLICKHOUSE_DB", "default")

            cls._client = clickhouse_connect.get_client(
                host=host,
                port=port,
                username=username,
                password=password,
                database=database,
            )
            logger.info(f"ClickHouse client connected to {host}:{port}/{database}")
        return cls._client

    @classmethod
    def reset_client(cls) -> None:
        """Reset client (useful for testing)."""
        cls._client = None

    @classmethod
    def ensure_table(cls, table_name: str = "bars_1m_spot") -> None:
        """Ensure the spot candles table exists with proper schema.

        Creates table if it doesn't exist.
        Schema:
        - ts: DateTime (UTC)
        - instrument_id: String (e.g., 'BTC-USD')
        - o: Float64 (open)
        - h: Float64 (high)
        - l: Float64 (low)
        - c: Float64 (close)
        - volume_base: Float64
        - volume_quote: Float64
        """
        client = cls.get_client()
        create_table_query = f"""
        CREATE TABLE IF NOT EXISTS {table_name}
        (
            ts DateTime('UTC'),
            instrument_id String,
            o Float64,
            h Float64,
            l Float64,
            c Float64,
            volume_base Float64,
            volume_quote Float64
        )
        ENGINE = MergeTree()
        ORDER BY (instrument_id, ts)
        PARTITION BY toYYYYMM(ts)
        """
        client.command(create_table_query)
        logger.info(f"Table {table_name} ensured")

    @classmethod
    def ensure_all_tables(cls) -> None:
        """Ensure all granularity tables exist."""
        tables = {
            "1m": "bars_1m_spot",
            "5m": "bars_5m_spot",
            "15m": "bars_15m_spot",
            "1h": "bars_1h_spot",
            "4h": "bars_4h_spot",
            "1d": "bars_1d_spot",
        }
        for granularity, table_name in tables.items():
            cls.ensure_table(table_name)

