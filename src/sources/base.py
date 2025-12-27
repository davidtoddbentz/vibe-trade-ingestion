"""Base classes for exchange adapters."""

from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import List, Optional

from ..models.candle import Candle


class ExchangeError(Exception):
    """Base exception for exchange-related errors."""

    pass


class Symbol(str, Enum):
    """Exchange-agnostic symbol enumeration."""

    BTC = "BTC"
    ETH = "ETH"
    SOL = "SOL"
    ADA = "ADA"
    DOT = "DOT"
    BNB = "BNB"
    XRP = "XRP"
    DOGE = "DOGE"
    TRX = "TRX"
    AVAX = "AVAX"
    SHIB = "SHIB"
    MATIC = "MATIC"
    LINK = "LINK"
    UNI = "UNI"
    ATOM = "ATOM"


def parse_symbol_string(symbol_str: str) -> Symbol:
    """Parse symbol string to Symbol enum.

    Handles different symbol formats:
    - "BTC-USD" -> Symbol.BTC
    - "BTC-USDC" -> Symbol.BTC
    - "BTC" -> Symbol.BTC

    Args:
        symbol_str: Symbol string in various formats

    Returns:
        Symbol enum value

    Raises:
        ValueError: If symbol string cannot be parsed
    """
    symbol_str = symbol_str.strip().upper()

    if "-" in symbol_str:
        base_symbol = symbol_str.split("-")[0]
    else:
        base_symbol = symbol_str

    try:
        return Symbol(base_symbol)
    except ValueError:
        symbol_map = {
            "BTC-USD": Symbol.BTC,
            "BTC-USDC": Symbol.BTC,
            "ETH-USD": Symbol.ETH,
            "ETH-USDC": Symbol.ETH,
        }
        if symbol_str in symbol_map:
            return symbol_map[symbol_str]
        raise ValueError(f"Unsupported symbol: {symbol_str}")


class Granularity(str, Enum):
    """Exchange-agnostic granularity enumeration."""

    ONE_MINUTE = "1m"
    FIVE_MINUTE = "5m"
    FIFTEEN_MINUTE = "15m"
    ONE_HOUR = "1h"
    FOUR_HOUR = "4h"
    ONE_DAY = "1d"


class ExchangeAdapter(ABC):
    """Base class for exchange adapters."""

    def __init__(self, portfolio_id: str = "default"):
        """Initialize exchange adapter."""
        self.portfolio_id = portfolio_id

    @abstractmethod
    def get_candles(
        self,
        symbol: Symbol,
        symbol_string: str,
        start_time: datetime,
        end_time: datetime,
        granularity: Granularity = Granularity.ONE_MINUTE,
        limit: Optional[int] = None,
    ) -> List[Candle]:
        """Get historical candle data for a symbol.

        Args:
            symbol: Symbol enum (e.g., Symbol.BTC)
            symbol_string: Full symbol string with quote currency (e.g., "BTC-USD")
            start_time: Start time for the data range
            end_time: End time for the data range
            granularity: Granularity enum
            limit: Maximum number of candles (optional)

        Returns:
            List of Candle objects with OHLCV data

        Raises:
            ExchangeError: If unable to fetch candle data
        """
        pass

