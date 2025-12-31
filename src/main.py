"""Real-time Coinbase SPOT data ingestion service.

Fetches 1-minute candles every minute, running 5 seconds after each minute.
"""

import logging
import os
import signal
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv

# Load .env file if it exists
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# Imports after logging setup (required for proper logging configuration)
from src.config import SystemConfig  # noqa: E402
from src.ingestion.realtime_ingestor import RealtimeIngestor  # noqa: E402
from src.sources.coinbase import CoinbaseExchangeAdapter  # noqa: E402

# Global flag for graceful shutdown
shutdown = False


def signal_handler(sig, frame):
    """Handle shutdown signals gracefully."""
    global shutdown
    logger.info("\n🛑 Shutting down...")
    shutdown = True


def get_next_run_time() -> datetime:
    """Calculate the next time to run (5 seconds after the next minute).

    Returns:
        Next run time (at :05 seconds past the minute)
    """
    now = datetime.now(timezone.utc)

    # Get the start of the next minute
    next_minute = now.replace(second=0, microsecond=0) + timedelta(minutes=1)

    # Add 5 seconds
    next_run = next_minute.replace(second=5)

    return next_run


def sleep_until(target_time: datetime):
    """Sleep until the target time.

    Args:
        target_time: Target datetime to sleep until
    """
    now = datetime.now(timezone.utc)
    sleep_seconds = (target_time - now).total_seconds()

    if sleep_seconds > 0:
        logger.debug(f"Sleeping {sleep_seconds:.2f} seconds until {target_time}")
        time.sleep(sleep_seconds)
    elif sleep_seconds < 0:
        logger.warning(f"Target time {target_time} is in the past, running immediately")


def main():
    """Main entry point for real-time ingestion."""
    logger.info("🚀 Starting Coinbase SPOT ingestion service...")

    try:
        # Load configuration
        system_config = SystemConfig.from_env()
        logger.info("✅ Configuration loaded")
        logger.info(f"   - Coinbase Environment: {system_config.coinbase_environment}")
        logger.info(
            f"   - API Key: {system_config.coinbase_api_key[:50]}..."
            if len(system_config.coinbase_api_key) > 50
            else f"   - API Key: {system_config.coinbase_api_key}"
        )

        # Get symbols from environment
        symbols_str = os.getenv("COINBASE_SYMBOLS", "BTC-USD,ETH-USD")
        symbols = [s.strip() for s in symbols_str.split(",") if s.strip()]
        logger.info(f"   - Symbols: {symbols}")

        if not symbols:
            raise ValueError("No symbols configured. Set COINBASE_SYMBOLS environment variable.")

        # Initialize exchange adapter
        exchange_adapter = CoinbaseExchangeAdapter(
            portfolio_id="system-ingestion",
            api_key=system_config.coinbase_api_key,
            api_secret=system_config.coinbase_api_secret,
            environment=system_config.coinbase_environment,
        )
        logger.info("✅ Exchange adapter initialized")

        # Initialize ingestor
        ingestor = RealtimeIngestor(exchange_adapter)
        logger.info("✅ Real-time ingestor initialized")

        # Register signal handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        logger.info("📡 Starting ingestion loop (runs at :05 seconds past each minute)...")
        logger.info("   Press Ctrl+C to stop\n")

        # Main loop
        while not shutdown:
            try:
                # Calculate next run time
                next_run = get_next_run_time()
                logger.info(f"⏰ Next fetch scheduled for {next_run}")

                # Sleep until next run time
                sleep_until(next_run)

                if shutdown:
                    break

                # Fetch candles for all symbols
                logger.info(f"🔄 Fetching candles at {datetime.now(timezone.utc)}...")
                results = ingestor.fetch_all_symbols(symbols)

                # Log results
                successful = sum(1 for candle in results.values() if candle is not None)
                failed = len(results) - successful
                logger.info(f"✅ Fetched {successful} candles, {failed} failed")

                # TODO: Publish to Pub/Sub here (later)
                for symbol, candle in results.items():
                    if candle:
                        # For now, just log - Pub/Sub will be added later
                        logger.debug(
                            f"  {symbol}: {candle.timestamp} "
                            f"O:{candle.open} H:{candle.high} "
                            f"L:{candle.low} C:{candle.close} V:{candle.volume}"
                        )

            except KeyboardInterrupt:
                logger.info("Interrupted by user")
                break
            except Exception as e:
                logger.error(f"Error in ingestion loop: {e}", exc_info=True)
                # Continue running even if one fetch fails
                time.sleep(1)

    except KeyboardInterrupt:
        logger.info("Shutting down...")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        logger.info("✅ Service stopped")


if __name__ == "__main__":
    main()
