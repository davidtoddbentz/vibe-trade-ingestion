"""Real-time Coinbase SPOT data ingestion service.

Fetches 1-minute candles every minute, running 5 seconds after each minute.
"""

import logging
import os
import signal
import sys
import threading
import time
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
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
from src.publishers.pubsub_publisher import PubSubPublisher  # noqa: E402
from src.sources.coinbase import CoinbaseExchangeAdapter  # noqa: E402

# Global flag for graceful shutdown
shutdown = False


class HealthCheckHandler(BaseHTTPRequestHandler):
    """Simple health check handler for Cloud Run."""

    def do_GET(self):
        """Handle GET requests for health checks."""
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"OK")

    def log_message(self, format, *args):
        """Suppress HTTP server logs."""
        pass


def start_health_server(port: int = 8080):
    """Start a simple HTTP server for Cloud Run health checks.

    Args:
        port: Port to listen on (default: 8080)
    """

    def run_server():
        server = HTTPServer(("", port), HealthCheckHandler)
        logger.info(f"🏥 Health check server listening on port {port}")
        while not shutdown:
            server.handle_request()
        server.server_close()
        logger.info("🏥 Health check server stopped")

    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()
    return thread


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
    """Sleep until the target time, checking for shutdown signals periodically.

    Args:
        target_time: Target datetime to sleep until
    """
    now = datetime.now(timezone.utc)
    sleep_seconds = (target_time - now).total_seconds()

    if sleep_seconds > 0:
        logger.info(
            f"⏳ Waiting {sleep_seconds:.1f} seconds until {target_time} (next fetch at :05)"
        )
        # Sleep in 1-second chunks to allow quick shutdown
        while sleep_seconds > 0 and not shutdown:
            chunk = min(1.0, sleep_seconds)
            time.sleep(chunk)
            sleep_seconds = (target_time - datetime.now(timezone.utc)).total_seconds()
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

        # Initialize Pub/Sub publisher
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "")
        if not project_id:
            logger.warning(
                "GOOGLE_CLOUD_PROJECT not set - Pub/Sub publishing will be disabled. "
                "Set GOOGLE_CLOUD_PROJECT environment variable to enable."
            )
            pubsub_publisher = None
        else:
            pubsub_publisher = PubSubPublisher(project_id)
            logger.info(f"✅ Pub/Sub publisher initialized (project: {project_id})")

        # Register signal handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Start health check server for Cloud Run
        port = int(os.getenv("PORT", "8080"))
        start_health_server(port)

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

                # Publish to Pub/Sub
                if pubsub_publisher:
                    publish_results = pubsub_publisher.publish_candles(results)
                    published = sum(1 for msg_id in publish_results.values() if msg_id is not None)
                    logger.info(f"📤 Published {published} candles to Pub/Sub")
                else:
                    # Log candles when Pub/Sub is not available
                    for symbol, candle in results.items():
                        if candle:
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
