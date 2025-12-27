"""Storage service for ClickHouse."""

import logging
from datetime import datetime
from typing import List, Optional

from ..db.clickhouse_client import ClickHouseClient
from ..models.bar_data import BarData
from ..models.results import StorageResult

logger = logging.getLogger(__name__)


class StorageService:
    """Storage service for market data."""

    def __init__(self):
        """Initialize storage service."""
        self.client = ClickHouseClient.get_client()
        ClickHouseClient.ensure_all_tables()

    async def store_spot_bars(
        self, bars: List[BarData], granularity: Optional[str] = None
    ) -> StorageResult:
        """Store spot market bars in ClickHouse.

        Args:
            bars: List of bar data to store
            granularity: Optional granularity string (e.g., '1m', '1h', '1d').
                If not provided, defaults to '1m'.
        """
        start_time = datetime.now()
        errors: List[str] = []
        try:
            if not bars:
                return StorageResult(
                    success=False,
                    records_stored=0,
                    errors=["No bars to store"],
                    execution_time_ms=0,
                )

            # Map granularity to table name
            table_map = {
                "1m": "bars_1m_spot",
                "5m": "bars_5m_spot",
                "15m": "bars_15m_spot",
                "1h": "bars_1h_spot",
                "4h": "bars_4h_spot",
                "1d": "bars_1d_spot",
            }
            table_name = table_map.get(granularity or "1m", "bars_1m_spot")

            # Ensure table exists
            ClickHouseClient.ensure_table(table_name)

            # Convert BarData to rows
            rows = []
            for bar in bars:
                rows.append(
                    (
                        bar.ts,
                        bar.instrument_id,
                        bar.o,
                        bar.h,
                        bar.l,
                        bar.c,
                        bar.volume_base,
                        bar.volume_quote,
                    )
                )

            # Insert data
            self.client.insert(
                table_name,
                rows,
                column_names=[
                    "ts",
                    "instrument_id",
                    "o",
                    "h",
                    "l",
                    "c",
                    "volume_base",
                    "volume_quote",
                ],
            )

            stored_count = len(rows)
            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
            logger.info(f"Stored {stored_count} spot bars in {table_name}")

            return StorageResult(
                success=True,
                records_stored=stored_count,
                errors=errors,
                execution_time_ms=execution_time,
            )
        except Exception as e:
            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
            error_msg = f"Failed to store spot bars: {str(e)}"
            errors.append(error_msg)
            logger.error(error_msg, exc_info=True)
            return StorageResult(
                success=False,
                records_stored=0,
                errors=errors,
                execution_time_ms=execution_time,
            )

    async def get_latest_timestamp(
        self, symbol: str, granularity: str
    ) -> Optional[datetime]:
        """Get the latest timestamp for a symbol and granularity.

        Args:
            symbol: Trading pair symbol (e.g., "BTC-USD")
            granularity: Granularity string (e.g., "1m", "1h")

        Returns:
            Latest timestamp or None if no data exists
        """
        try:
            # Normalize symbol
            db_symbol = symbol if "-" in symbol else f"{symbol}-USD"

            # Map granularity to table name
            table_map = {
                "1m": "bars_1m_spot",
                "5m": "bars_5m_spot",
                "15m": "bars_15m_spot",
                "1h": "bars_1h_spot",
                "4h": "bars_4h_spot",
                "1d": "bars_1d_spot",
            }
            table_name = table_map.get(granularity, "bars_1m_spot")

            query = f"""
            SELECT max(ts) as latest
            FROM {table_name}
            WHERE instrument_id = %(symbol)s
            """
            result = self.client.query(query, parameters={"symbol": db_symbol})
            if result.result_rows:
                latest = result.result_rows[0][0]
                return latest if latest else None
            return None
        except Exception as e:
            logger.error(f"Failed to get latest timestamp for {symbol}: {e}")
            return None

