#!/usr/bin/env python3
"""Batch job entry point for running ingestion jobs directly."""

import asyncio
import logging
import os
import sys
from datetime import datetime, timezone
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

# Import after path setup
from src.config import IngestionConfig, SystemConfig
from src.ingestion.spot_ingestor import SpotIngestor
from src.ingestion.storage_service import StorageService
from src.sources.base import Granularity
from src.sources.coinbase import CoinbaseExchangeAdapter


async def main():
    """Run the spot ingestion job directly."""
    logger.info("🚀 Starting batch spot ingestion job...")

    try:
        # Load system configuration
        try:
            system_config = SystemConfig.from_env()
            system_config.validate()
            logger.info("✅ System configuration loaded")
            logger.info(f"   - Coinbase Environment: {system_config.coinbase_environment}")
        except ValueError as config_error:
            error_msg = (
                f"❌ CRITICAL: System configuration invalid: {config_error}\n"
                f"Required environment variables:\n"
                f"  - COINBASE_API_KEY\n"
                f"  - COINBASE_API_SECRET\n"
                f"Optional: COINBASE_ENVIRONMENT (default: sandbox)"
            )
            logger.error(error_msg)
            raise ValueError(error_msg) from config_error

        # Load ClickHouse configuration
        config = IngestionConfig()
        logger.info("✅ ClickHouse configuration loaded")
        logger.info(f"   - ClickHouse Host: {config.clickhouse_host}")
        logger.info(f"   - ClickHouse Port: {config.clickhouse_port}")
        logger.info(f"   - ClickHouse User: {config.clickhouse_user}")
        logger.info(f"   - ClickHouse Database: {config.clickhouse_database}")

        # Initialize storage service
        storage_service = StorageService()
        logger.info("✅ Storage service initialized")

        # Create exchange adapter
        exchange_name = os.getenv("EXCHANGE_NAME", "coinbase")
        logger.info(f"   - Exchange: {exchange_name}")

        if exchange_name.lower() == "coinbase":
            exchange_adapter = CoinbaseExchangeAdapter(
                portfolio_id="system-ingestion",
                api_key=system_config.coinbase_api_key,
                api_secret=system_config.coinbase_api_secret,
                environment=system_config.coinbase_environment,
            )
        else:
            raise ValueError(f"Unsupported exchange: {exchange_name}")

        logger.info(f"✅ Exchange adapter created: {type(exchange_adapter).__name__}")

        # Create spot ingestor
        spot_ingestor = SpotIngestor(storage_service, exchange_adapter)
        logger.info("✅ Spot ingestor created")

        # Get configuration
        default_symbols = (
            "BTC-USD,ETH-USD"
        )
        symbols = os.getenv("INGESTION_SYMBOLS", default_symbols).split(",")
        symbols = [s.strip() for s in symbols if s.strip()]
        granularity = os.getenv("INGESTION_GRANULARITY", "1m")

        # Optional time range parameters
        ingestion_days = os.getenv("INGESTION_DAYS")
        ingestion_start_time = os.getenv("INGESTION_START_TIME")
        ingestion_end_time = os.getenv("INGESTION_END_TIME")

        logger.info(f"   - Symbols: {symbols}")
        logger.info(f"   - Granularity: {granularity}")

        if ingestion_days:
            logger.info(f"   - Ingestion Days: {ingestion_days}")
        if ingestion_start_time:
            logger.info(f"   - Start Time: {ingestion_start_time}")
        if ingestion_end_time:
            logger.info(f"   - End Time: {ingestion_end_time}")

        # Process symbols
        granularity_map = {
            "1m": Granularity.ONE_MINUTE,
            "5m": Granularity.FIVE_MINUTE,
            "15m": Granularity.FIFTEEN_MINUTE,
            "1h": Granularity.ONE_HOUR,
            "4h": Granularity.FOUR_HOUR,
            "1d": Granularity.ONE_DAY,
        }
        granularity_enum = granularity_map.get(granularity, Granularity.ONE_MINUTE)

        logger.info("🚀 Starting data ingestion...")

        # Validate parameter combinations
        if ingestion_days and (ingestion_start_time or ingestion_end_time):
            raise ValueError(
                "INGESTION_DAYS cannot be used together with "
                "INGESTION_START_TIME/INGESTION_END_TIME. Use one or the other."
            )

        # Validate time range parameters
        if (ingestion_start_time and not ingestion_end_time) or (
            ingestion_end_time and not ingestion_start_time
        ):
            raise ValueError(
                "Both INGESTION_START_TIME and INGESTION_END_TIME must be "
                "provided together, or neither should be provided"
            )

        # Check if time range parameters are provided
        if ingestion_start_time and ingestion_end_time:
            # Parse ISO format timestamps
            try:
                start_time = datetime.fromisoformat(
                    ingestion_start_time.replace("Z", "+00:00")
                )
                end_time = datetime.fromisoformat(ingestion_end_time.replace("Z", "+00:00"))
                # Ensure timezone-aware
                if start_time.tzinfo is None:
                    start_time = start_time.replace(tzinfo=timezone.utc)
                if end_time.tzinfo is None:
                    end_time = end_time.replace(tzinfo=timezone.utc)

                # Validate time range
                if start_time >= end_time:
                    raise ValueError(
                        "INGESTION_START_TIME must be before INGESTION_END_TIME"
                    )

                logger.info(f"Ingesting time range: {start_time} to {end_time}")
                result = await spot_ingestor.ingest_multiple_symbols_range(
                    symbols, granularity_enum, start_time, end_time
                )
            except ValueError as e:
                logger.error(f"Invalid time format: {e}")
                raise ValueError(
                    f"Invalid time format. Use ISO format (e.g., "
                    f"2025-01-27T00:00:00Z): {e}"
                )
        elif ingestion_days:
            # Use backfill with specified number of days
            try:
                days = int(ingestion_days)
                logger.info(f"Backfilling {days} days of data")
                result = await spot_ingestor.ingest_multiple_symbols_backfill(
                    symbols, granularity_enum, days
                )
            except ValueError as e:
                logger.error(f"Invalid days value: {e}")
                raise ValueError(f"INGESTION_DAYS must be a valid integer: {e}")
        else:
            # Default: append latest bars
            result = await spot_ingestor.ingest_multiple_symbols(symbols, granularity_enum)

        logger.info(f"✅ Ingestion completed: {result}")

        # Exit with success
        sys.exit(0)

    except Exception as e:
        logger.error(f"❌ Job failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

