"""Result models for ingestion operations."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, List, Optional

from ..sources.base import Granularity, Symbol


@dataclass
class StorageResult:
    """Result of storage operation."""

    success: bool
    records_stored: int
    errors: List[str]
    execution_time_ms: int


@dataclass
class AppendResult:
    """Result of append operation."""

    symbol: Symbol
    granularity: Granularity
    bars_inserted: int
    status: str  # "success", "no_new_data", "error"
    execution_time_ms: int
    errors: Optional[List[str]] = None

    def __post_init__(self):
        """Initialize errors list if None."""
        if self.errors is None:
            self.errors = []


@dataclass
class IngestionResult:
    """Result of ingestion operation."""

    symbol: Symbol
    granularity: Granularity
    start_time: datetime
    end_time: datetime
    candles_fetched: int
    bars_inserted: int
    status: str  # "success", "error"
    execution_time_ms: int
    errors: Optional[List[str]] = None

    def __post_init__(self):
        """Initialize errors list if None."""
        if self.errors is None:
            self.errors = []

