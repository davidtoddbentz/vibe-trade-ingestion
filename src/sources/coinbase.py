"""Coinbase Advanced Trade exchange adapter."""

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional

from coinbase.rest import RESTClient

from ..models.candle import Candle
from .base import ExchangeAdapter, ExchangeError, Granularity, Symbol

logger = logging.getLogger(__name__)


class CoinbaseExchangeAdapter(ExchangeAdapter):
    """Coinbase Advanced Trade exchange adapter."""

    def __init__(
        self,
        portfolio_id: str = "system-ingestion",
        api_key: str = "",
        api_secret: str = "",
        environment: str = "sandbox",
        rest_client: Optional[RESTClient] = None,
    ):
        """Initialize Coinbase Advanced Trade adapter.

        Args:
            portfolio_id: Portfolio identifier
            api_key: Coinbase API key
            api_secret: Coinbase API secret (private key in PEM format)
            environment: API environment (sandbox/live)
            rest_client: Optional REST client for testing
        """
        super().__init__(portfolio_id)
        self.environment = environment
        self.api_key = api_key
        self.api_secret = api_secret

        if not api_key or not api_secret:
            raise ValueError("API key and secret are required for Coinbase Advanced Trade API")

        # Normalize PEM key
        if api_secret.startswith("-----BEGIN"):
            if "\\n" in api_secret and "\n" not in api_secret:
                api_secret = api_secret.replace("\\n", "\n")
            api_secret = api_secret.rstrip("\n\r")
            self.api_secret = api_secret
        else:
            self.api_secret = api_secret

        # Create REST client
        if rest_client:
            self.rest_client = rest_client
        else:
            try:
                if self.api_secret.startswith("-----BEGIN"):
                    if "-----END" not in self.api_secret:
                        raise ValueError("Invalid PEM key: missing END marker")
                    lines = self.api_secret.split("\n")
                    if len(lines) < 3:
                        raise ValueError("Invalid PEM key: too few lines")

                self.rest_client = RESTClient(api_key=self.api_key, api_secret=self.api_secret)
                logger.info("RESTClient created successfully")
            except Exception as e:
                error_msg = (
                    f"Failed to create Coinbase RESTClient: {e}\n"
                    f"Please verify:\n"
                    f"  1. The API key is correct\n"
                    f"  2. The private key is a valid PEM format key\n"
                    f"  3. The key has proper newlines (not escaped \\n strings)"
                )
                logger.error(error_msg)
                raise ExchangeError(error_msg) from e

    def _normalize_symbol(self, symbol: Symbol, symbol_string: str) -> str:
        """Normalize symbol for Coinbase.

        Args:
            symbol: Base symbol (BTC, ETH, etc.)
            symbol_string: Full symbol string with quote currency (e.g., "ETH-USDC", "BTC-USD")

        Returns:
            Coinbase product ID (e.g., "BTC-USDC", "ETH-USD")
        """
        if not symbol_string or "-" not in symbol_string:
            raise ValueError(
                f"Symbol string must include quote currency (e.g., 'ETH-USDC', 'BTC-USD'). "
                f"Got: {symbol_string}"
            )

        parts = symbol_string.upper().split("-")
        if len(parts) != 2:
            raise ValueError(
                f"Invalid symbol format. Expected 'BASE-QUOTE' (e.g., 'ETH-USDC'). "
                f"Got: {symbol_string}"
            )

        base_symbol, quote_currency = parts[0], parts[1]

        if base_symbol != symbol.value:
            raise ValueError(
                f"Base symbol mismatch. Symbol enum is {symbol.value} but symbol_string has {base_symbol}. "
                f"Symbol string: {symbol_string}"
            )

        return f"{symbol.value}-{quote_currency}"

    def _normalize_granularity(self, granularity: Granularity) -> str:
        """Convert granularity to Coinbase format."""
        mapping = {
            "1m": "ONE_MINUTE",
            "5m": "FIVE_MINUTE",
            "15m": "FIFTEEN_MINUTE",
            "1h": "ONE_HOUR",
            "4h": "FOUR_HOUR",
            "1d": "ONE_DAY",
        }
        if hasattr(granularity, "value"):
            return mapping[granularity.value]
        return mapping[granularity]

    def get_candles(
        self,
        symbol: Symbol,
        symbol_string: str,
        start_time: datetime,
        end_time: datetime,
        granularity: Granularity = Granularity.ONE_MINUTE,
        limit: Optional[int] = None,
    ) -> List[Candle]:
        """Get historical candle data for a symbol."""
        logger.info(f"Fetching candles for {symbol} from {start_time} to {end_time}")
        try:
            normalized_symbol = self._normalize_symbol(symbol, symbol_string)
            coinbase_granularity = self._normalize_granularity(granularity)

            if start_time.tzinfo is None:
                start_time = start_time.replace(tzinfo=timezone.utc)
            if end_time.tzinfo is None:
                end_time = end_time.replace(tzinfo=timezone.utc)

            candles = self._fetch_candles_paginated(
                normalized_symbol, start_time, end_time, coinbase_granularity
            )
            logger.info(f"Successfully fetched {len(candles)} candles for {symbol}")
            return candles

        except Exception as e:
            logger.error(f"Failed to get candles for {symbol}: {e}")
            raise ExchangeError(f"Failed to get candles for {symbol}: {e}")

    def _fetch_candles_paginated(
        self,
        normalized_symbol: str,
        start_time: datetime,
        end_time: datetime,
        coinbase_granularity: str,
    ) -> List[Candle]:
        """Fetch candles with pagination."""
        from datetime import timedelta

        all_candles = []
        current_start = start_time
        max_candles_per_request = 350
        chunk_count = 0

        while current_start < end_time:
            chunk_count += 1
            chunk_end = min(
                current_start + timedelta(minutes=max_candles_per_request), end_time
            )

            logger.debug(f"Chunk {chunk_count}: {current_start} to {chunk_end}")
            chunk_candles = self._fetch_candles_chunk(
                normalized_symbol, current_start, chunk_end, coinbase_granularity
            )
            all_candles.extend(chunk_candles)

            current_start = chunk_end + timedelta(minutes=1)

            if current_start >= end_time:
                break

        all_candles.sort(key=lambda c: c.timestamp)
        return all_candles

    def _fetch_candles_chunk(
        self,
        normalized_symbol: str,
        chunk_start: datetime,
        chunk_end: datetime,
        coinbase_granularity: str,
    ) -> List[Candle]:
        """Fetch a single chunk of candles."""
        try:
            response = self.rest_client.get_candles(
                product_id=normalized_symbol,
                start=int(chunk_start.timestamp()),
                end=int(chunk_end.timestamp()),
                granularity=coinbase_granularity,
            )

            if not response or not getattr(response, "candles", None):
                logger.warning(f"No candles returned for {normalized_symbol}")
                return []

            candles = self._parse_sdk_candles(response.candles)
            return candles

        except Exception as e:
            logger.error(f"Failed to fetch candles for {normalized_symbol}: {e}")
            raise ExchangeError(f"Failed to fetch candles: {e}")

    def _parse_sdk_candles(self, candles_data) -> List[Candle]:
        """Parse SDK candle data into Candle objects."""
        candles = []
        for candle_data in candles_data:
            if isinstance(candle_data.start, datetime):
                timestamp = candle_data.start
            else:
                timestamp = datetime.fromtimestamp(int(candle_data.start), tz=timezone.utc)

            candles.append(
                Candle(
                    timestamp=timestamp,
                    open=float(Decimal(str(candle_data.open))),
                    high=float(Decimal(str(candle_data.high))),
                    low=float(Decimal(str(candle_data.low))),
                    close=float(Decimal(str(candle_data.close))),
                    volume=float(Decimal(str(candle_data.volume))),
                )
            )
        return candles

