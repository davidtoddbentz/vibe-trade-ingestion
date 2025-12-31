"""Canonical candle model."""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class Candle:
    """OHLCV candle data."""

    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
