"""Shared test fixtures and utilities."""

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from src.models.candle import Candle


class MockCandleData:
    """Mock candle data object that mimics Coinbase SDK response."""

    def __init__(self, start, open_price, high, low, close, volume):
        """Initialize mock candle data.

        Args:
            start: Start timestamp (datetime or int)
            open_price: Open price
            high: High price
            low: Low price
            close: Close price
            volume: Volume
        """
        self.start = start
        self.open = Decimal(str(open_price))
        self.high = Decimal(str(high))
        self.low = Decimal(str(low))
        self.close = Decimal(str(close))
        self.volume = Decimal(str(volume))


class MockCandlesResponse:
    """Mock response object that mimics Coinbase get_candles response."""

    def __init__(self, candles_data: list[MockCandleData]):
        """Initialize mock response.

        Args:
            candles_data: List of MockCandleData objects
        """
        self.candles = candles_data


@pytest.fixture
def mock_rest_client():
    """Create a mock Coinbase RESTClient."""
    return MagicMock()


@pytest.fixture
def sample_candle_data():
    """Create sample candle data for testing."""
    base_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

    return [
        MockCandleData(
            start=base_time,
            open_price=50000.0,
            high=50100.0,
            low=49900.0,
            close=50050.0,
            volume=1.5,
        ),
        MockCandleData(
            start=base_time.replace(minute=1),
            open_price=50050.0,
            high=50200.0,
            low=50000.0,
            close=50100.0,
            volume=2.0,
        ),
    ]


@pytest.fixture
def sample_candles_response(sample_candle_data):
    """Create a mock candles response."""
    return MockCandlesResponse(sample_candle_data)


@pytest.fixture
def sample_candles():
    """Create sample Candle objects for testing."""
    base_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

    return [
        Candle(
            timestamp=base_time,
            open=50000.0,
            high=50100.0,
            low=49900.0,
            close=50050.0,
            volume=1.5,
        ),
        Candle(
            timestamp=base_time.replace(minute=1),
            open=50050.0,
            high=50200.0,
            low=50000.0,
            close=50100.0,
            volume=2.0,
        ),
    ]


def create_mock_candle_response(
    timestamp: datetime,
    open_price: float,
    high: float,
    low: float,
    close: float,
    volume: float,
) -> MockCandleData:
    """Helper to create a mock candle response.

    Args:
        timestamp: Candle timestamp
        open_price: Open price
        high: High price
        low: Low price
        close: Close price
        volume: Volume

    Returns:
        MockCandleData object
    """
    return MockCandleData(
        start=timestamp,
        open_price=open_price,
        high=high,
        low=low,
        close=close,
        volume=volume,
    )


def create_mock_candles_response(candles: list[tuple]) -> MockCandlesResponse:
    """Helper to create a mock candles response from tuples.

    Args:
        candles: List of tuples (timestamp, open, high, low, close, volume)

    Returns:
        MockCandlesResponse object
    """
    candle_data = [
        MockCandleData(
            start=ts,
            open_price=open_price,
            high=high,
            low=low,
            close=close,
            volume=volume,
        )
        for ts, open_price, high, low, close, volume in candles
    ]
    return MockCandlesResponse(candle_data)

