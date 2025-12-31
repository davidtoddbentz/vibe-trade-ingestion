"""Real-time ingestion service for fetching 1-minute candles."""

import logging
from datetime import datetime, timedelta, timezone

from ..models.candle import Candle
from ..sources.base import ExchangeAdapter, Granularity, parse_symbol_string

logger = logging.getLogger(__name__)


class RealtimeIngestor:
    """Real-time ingestor that fetches 1-minute candles every minute."""

    def __init__(self, exchange_adapter: ExchangeAdapter):
        """Initialize real-time ingestor.

        Args:
            exchange_adapter: Exchange adapter for fetching candles
        """
        self.exchange = exchange_adapter

    def fetch_latest_1m_candle(self, symbol_string: str) -> Candle | None:
        """Fetch the most recent completed 1-minute candle.

        Args:
            symbol_string: Symbol string (e.g., "BTC-USD")

        Returns:
            Most recent candle or None if not available
        """
        try:
            symbol = parse_symbol_string(symbol_string)

            # Get current time and calculate the previous completed minute
            now = datetime.now(timezone.utc)
            # Round down to the start of the current minute
            current_minute_start = now.replace(second=0, microsecond=0)
            # Previous completed minute is 1 minute ago
            # Fetch from 1 minute ago to current minute start to get the completed candle
            end_time = current_minute_start
            start_time = end_time - timedelta(minutes=1)

            logger.debug(f"Fetching candles for {symbol_string} from {start_time} to {end_time}")

            candles = self.exchange.get_candles(
                symbol=symbol,
                symbol_string=symbol_string,
                start_time=start_time,
                end_time=end_time,
                granularity=Granularity.ONE_MINUTE,
            )

            if not candles:
                logger.warning(f"No candles returned for {symbol_string}")
                return None

            # Get the most recent candle (should be the completed one)
            latest_candle = max(candles, key=lambda c: c.timestamp)

            logger.info(
                f"✅ Fetched 1m candle for {symbol_string}: "
                f"{latest_candle.timestamp} O:{latest_candle.open} "
                f"H:{latest_candle.high} L:{latest_candle.low} "
                f"C:{latest_candle.close} V:{latest_candle.volume}"
            )

            return latest_candle

        except Exception as e:
            logger.error(f"Failed to fetch candle for {symbol_string}: {e}", exc_info=True)
            return None

    def fetch_all_symbols(self, symbols: list[str]) -> dict:
        """Fetch latest candles for all symbols.

        Args:
            symbols: List of symbol strings

        Returns:
            Dictionary mapping symbol to candle (or None if failed)
        """
        results = {}
        for symbol_string in symbols:
            candle = self.fetch_latest_1m_candle(symbol_string)
            results[symbol_string] = candle
        return results
