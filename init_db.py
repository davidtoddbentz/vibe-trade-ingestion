#!/usr/bin/env python3
"""Initialize ClickHouse database with required tables."""

import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load .env file if it exists
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(env_path)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

from src.db.clickhouse_client import ClickHouseClient


def main():
    """Initialize ClickHouse database with all required tables."""
    logger.info("🗄️  Initializing ClickHouse database...")

    try:
        # Ensure all tables exist
        ClickHouseClient.ensure_all_tables()
        logger.info("✅ All tables initialized successfully")

        # Verify tables exist
        client = ClickHouseClient.get_client()
        tables = [
            "bars_1m_spot",
            "bars_5m_spot",
            "bars_15m_spot",
            "bars_1h_spot",
            "bars_4h_spot",
            "bars_1d_spot",
        ]

        logger.info("📊 Verifying tables...")
        for table in tables:
            try:
                result = client.query(f"EXISTS TABLE {table}")
                exists = result.result_rows[0][0] if result.result_rows else False
                if exists:
                    count_result = client.query(f"SELECT COUNT(*) FROM {table}")
                    count = count_result.result_rows[0][0] if count_result.result_rows else 0
                    logger.info(f"   ✅ {table}: {count:,} rows")
                else:
                    logger.warning(f"   ⚠️  {table}: Table does not exist")
            except Exception as e:
                logger.error(f"   ❌ {table}: Error - {e}")

        logger.info("✅ Database initialization complete!")
        return 0

    except Exception as e:
        logger.error(f"❌ Failed to initialize database: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())

