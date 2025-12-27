"""Spot data ingestion logic."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from ..models.bar_data import BarData
from ..models.candle import Candle
from ..models.results import AppendResult, IngestionResult
from ..sources.base import ExchangeAdapter, Granularity, Symbol
from .storage_service import StorageService

logger = logging.getLogger(__name__)


class SpotIngestor:
    """Orchestrates spot market data ingestion."""

    def __init__(
        self,
        storage_service: StorageService,
        exchange_adapter: ExchangeAdapter,
    ) -> None:
        """Initialize spot ingestor.

        Args:
            storage_service: Handles data storage
            exchange_adapter: Handles exchange communication
        """
        self.storage = storage_service
        self.exchange = exchange_adapter

    async def ingest_multiple_symbols(
        self, symbols: List[str], granularity: Granularity
    ) -> Dict[str, Any]:
        """Ingest data for multiple symbols.

        Args:
            symbols: List of symbol strings (e.g., ["BTC-USD", "ETH-USD"])
            granularity: Data granularity

        Returns:
            Dictionary with ingestion results
        """
        logger.info(f"Starting ingestion for {len(symbols)} symbols: {symbols}")

        results: Dict[str, Any] = {
            "job_name": "spot_ingestion",
            "status": "success",
            "symbols_processed": 0,
            "total_bars_inserted": 0,
            "errors": [],
            "execution_time_ms": 0,
        }

        start_time = datetime.now(timezone.utc)

        for symbol_str in symbols:
            try:
                logger.info(f"Processing {symbol_str}...")

                from ..sources.base import parse_symbol_string

                symbol = parse_symbol_string(symbol_str)

                result = await self.append_latest_bars(
                    symbol, granularity, symbol_string=symbol_str
                )

                if result.status == "success":
                    results["symbols_processed"] += 1
                    results["total_bars_inserted"] += result.bars_inserted
                    logger.info(f"✅ {symbol_str}: {result.bars_inserted} bars inserted")
                else:
                    error_msg = f"Failed to process {symbol_str}: {result.status}"
                    results["errors"].append(error_msg)
                    logger.error(error_msg)

            except Exception as e:
                error_msg = f"Error processing {symbol_str}: {str(e)}"
                results["errors"].append(error_msg)
                logger.error(error_msg, exc_info=True)
                continue

        end_time = datetime.now(timezone.utc)
        results["execution_time_ms"] = int((end_time - start_time).total_seconds() * 1000)

        if results["errors"]:
            results["status"] = "completed_with_errors"
        else:
            results["status"] = "success"

        logger.info(
            f"Ingestion completed: {results['symbols_processed']} symbols, "
            f"{results['total_bars_inserted']} bars"
        )
        return results

    async def ingest_multiple_symbols_range(
        self,
        symbols: List[str],
        granularity: Granularity,
        start_time: datetime,
        end_time: datetime,
    ) -> Dict[str, any]:
        """Ingest data for multiple symbols within a specific time range."""
        logger.info(
            f"Starting range ingestion for {len(symbols)} symbols: {symbols} "
            f"from {start_time} to {end_time}"
        )

        results: Dict[str, Any] = {
            "job_name": "spot_ingestion_range",
            "status": "success",
            "symbols_processed": 0,
            "total_bars_inserted": 0,
            "errors": [],
            "execution_time_ms": 0,
        }

        op_start = datetime.now(timezone.utc)

        for symbol_str in symbols:
            try:
                logger.info(f"Processing {symbol_str}...")

                from ..sources.base import parse_symbol_string

                symbol = parse_symbol_string(symbol_str)

                result = await self.ingest_range(
                    symbol, start_time, end_time, granularity, symbol_string=symbol_str
                )

                if result.status == "success":
                    results["symbols_processed"] += 1
                    results["total_bars_inserted"] += result.bars_inserted
                    logger.info(
                        f"✅ {symbol_str}: {result.bars_inserted} bars inserted "
                        f"({result.candles_fetched} candles fetched)"
                    )
                else:
                    error_msg = f"Failed to process {symbol_str}: {result.status}"
                    results["errors"].append(error_msg)
                    logger.error(error_msg)

            except Exception as e:
                error_msg = f"Error processing {symbol_str}: {str(e)}"
                results["errors"].append(error_msg)
                logger.error(error_msg, exc_info=True)
                continue

        op_end = datetime.now(timezone.utc)
        results["execution_time_ms"] = int((op_end - op_start).total_seconds() * 1000)

        if results["errors"]:
            results["status"] = "completed_with_errors"
        else:
            results["status"] = "success"

        logger.info(
            f"Range ingestion completed: {results['symbols_processed']} symbols, "
            f"{results['total_bars_inserted']} bars"
        )
        return results

    async def ingest_multiple_symbols_backfill(
        self, symbols: List[str], granularity: Granularity, days: int
    ) -> Dict[str, any]:
        """Backfill data for multiple symbols for a specified number of days."""
        logger.info(
            f"Starting backfill for {len(symbols)} symbols: {symbols} " f"for {days} days"
        )

        results: Dict[str, Any] = {
            "job_name": "spot_ingestion_backfill",
            "status": "success",
            "symbols_processed": 0,
            "total_bars_inserted": 0,
            "errors": [],
            "execution_time_ms": 0,
        }

        op_start = datetime.now(timezone.utc)

        for symbol_str in symbols:
            try:
                logger.info(f"Processing {symbol_str}...")

                from ..sources.base import parse_symbol_string

                symbol = parse_symbol_string(symbol_str)

                result = await self.backfill_bars(
                    symbol, days, granularity, symbol_string=symbol_str
                )

                if result.status == "success":
                    results["symbols_processed"] += 1
                    results["total_bars_inserted"] += result.bars_inserted
                    logger.info(
                        f"✅ {symbol_str}: {result.bars_inserted} bars inserted "
                        f"({result.candles_fetched} candles fetched)"
                    )
                else:
                    error_msg = f"Failed to process {symbol_str}: {result.status}"
                    results["errors"].append(error_msg)
                    logger.error(error_msg)

            except Exception as e:
                error_msg = f"Error processing {symbol_str}: {str(e)}"
                results["errors"].append(error_msg)
                logger.error(error_msg, exc_info=True)
                continue

        op_end = datetime.now(timezone.utc)
        results["execution_time_ms"] = int((op_end - op_start).total_seconds() * 1000)

        if results["errors"]:
            results["status"] = "completed_with_errors"
        else:
            results["status"] = "success"

        logger.info(
            f"Backfill completed: {results['symbols_processed']} symbols, "
            f"{results['total_bars_inserted']} bars"
        )
        return results

    async def backfill_bars(
        self,
        symbol: Symbol,
        days: int,
        granularity: Granularity,
        symbol_string: Optional[str] = None,
    ) -> IngestionResult:
        """Backfill historical bars for a symbol."""
        logger.info(f"Starting backfill for {symbol} - {days} days of {granularity} bars")

        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=days)
        op_start = datetime.now(timezone.utc)

        try:
            if not symbol_string:
                raise ValueError(
                    f"symbol_string is required for get_candles. "
                    f"Received symbol={symbol}, symbol_string={symbol_string}"
                )
            candles = self.exchange.get_candles(
                symbol=symbol,
                symbol_string=symbol_string,
                start_time=start_time,
                end_time=end_time,
                granularity=granularity,
            )

            logger.info(f"Fetched {len(candles)} candles for {symbol}")

            bars = self._candles_to_bars(candles, symbol, symbol_string=symbol_string)

            storage_result = await self.storage.store_spot_bars(
                bars, granularity=granularity.value
            )

            duration_ms = int((datetime.now(timezone.utc) - op_start).total_seconds() * 1000)

            return IngestionResult(
                symbol=symbol,
                granularity=granularity,
                start_time=start_time,
                end_time=end_time,
                candles_fetched=len(candles),
                bars_inserted=storage_result.records_stored,
                status="success" if storage_result.success else "error",
                execution_time_ms=duration_ms,
            )

        except Exception as e:
            logger.error(f"Backfill failed for {symbol}: {e}", exc_info=True)
            duration_ms = int((datetime.now(timezone.utc) - op_start).total_seconds() * 1000)
            return IngestionResult(
                symbol=symbol,
                granularity=granularity,
                start_time=start_time,
                end_time=end_time,
                candles_fetched=0,
                bars_inserted=0,
                status="error",
                execution_time_ms=duration_ms,
                errors=[str(e)],
            )

    async def append_latest_bars(
        self,
        symbol: Symbol,
        granularity: Granularity,
        symbol_string: Optional[str] = None,
    ) -> AppendResult:
        """Append latest bars for a symbol with gap detection."""
        logger.info(f"Appending latest {granularity} bars for {symbol}")

        op_start = datetime.now(timezone.utc)

        try:
            logger.debug(f"Getting latest timestamp for {symbol.value}, {granularity.value}")
            latest_ts = await self.storage.get_latest_timestamp(
                symbol.value, granularity.value
            )
            logger.debug(f"Latest timestamp: {latest_ts}")

            end_time = datetime.now(timezone.utc)
            if latest_ts is not None:
                if latest_ts.tzinfo is None:
                    latest_ts = latest_ts.replace(tzinfo=timezone.utc)
                gap_duration = end_time - latest_ts
                if gap_duration > timedelta(hours=6):
                    logger.warning(f"Large gap detected for {symbol}: {gap_duration}")

                max_gap = timedelta(days=7)
                if gap_duration > max_gap:
                    logger.warning(f"Gap too large ({gap_duration}), capping at {max_gap}")
                    start_time = end_time - max_gap
                else:
                    start_time = latest_ts + timedelta(seconds=1)
            else:
                start_time = self._get_initial_fetch_time(granularity, end_time)
                logger.info(
                    f"Empty database detected for {symbol}, "
                    f"fetching {start_time} to {end_time}"
                )

            logger.debug(f"Time range: {start_time} to {end_time}")

            if not symbol_string:
                symbol_string = f"{symbol.value}-USD"
                logger.debug(f"symbol_string not provided, defaulting to {symbol_string}")

            candles = self.exchange.get_candles(
                symbol=symbol,
                symbol_string=symbol_string,
                start_time=start_time,
                end_time=end_time,
                granularity=granularity,
            )
            logger.debug(f"Fetched {len(candles) if candles else 0} candles")

            if not candles:
                duration_ms = int(
                    (datetime.now(timezone.utc) - op_start).total_seconds() * 1000
                )
                return AppendResult(
                    symbol=symbol,
                    granularity=granularity,
                    bars_inserted=0,
                    status="no_new_data",
                    execution_time_ms=duration_ms,
                )

            logger.debug(f"Converting {len(candles)} candles to bars...")
            bars = self._candles_to_bars(candles, symbol, symbol_string=symbol_string)
            logger.debug(f"Converted to {len(bars)} bars")

            storage_result = await self.storage.store_spot_bars(
                bars, granularity=granularity.value
            )

            duration_ms = int((datetime.now(timezone.utc) - op_start).total_seconds() * 1000)

            return AppendResult(
                symbol=symbol,
                granularity=granularity,
                bars_inserted=storage_result.records_stored,
                status="success" if storage_result.success else "error",
                execution_time_ms=duration_ms,
                errors=storage_result.errors,
            )

        except Exception as e:
            logger.error(f"Append failed for {symbol}: {e}", exc_info=True)
            duration_ms = int((datetime.now(timezone.utc) - op_start).total_seconds() * 1000)
            return AppendResult(
                symbol=symbol,
                granularity=granularity,
                bars_inserted=0,
                status="error",
                execution_time_ms=duration_ms,
                errors=[str(e)],
            )

    async def ingest_range(
        self,
        symbol: Symbol,
        start_time: datetime,
        end_time: datetime,
        granularity: Granularity,
        symbol_string: Optional[str] = None,
    ) -> IngestionResult:
        """Ingest data for a specific time range."""
        logger.info(f"Ingesting {symbol} from {start_time} to {end_time}")

        op_start = datetime.now(timezone.utc)

        try:
            if not symbol_string:
                raise ValueError(
                    f"symbol_string is required for get_candles. "
                    f"Received symbol={symbol}, symbol_string={symbol_string}"
                )
            candles = self.exchange.get_candles(
                symbol=symbol,
                symbol_string=symbol_string,
                start_time=start_time,
                end_time=end_time,
                granularity=granularity,
            )

            bars = self._candles_to_bars(candles, symbol, symbol_string=symbol_string)
            storage_result = await self.storage.store_spot_bars(
                bars, granularity=granularity.value
            )

            duration_ms = int((datetime.now(timezone.utc) - op_start).total_seconds() * 1000)

            return IngestionResult(
                symbol=symbol,
                granularity=granularity,
                start_time=start_time,
                end_time=end_time,
                candles_fetched=len(candles),
                bars_inserted=storage_result.records_stored,
                status="success" if storage_result.success else "error",
                execution_time_ms=duration_ms,
                errors=storage_result.errors,
            )

        except Exception as e:
            logger.error(f"Range ingestion failed for {symbol}: {e}", exc_info=True)
            duration_ms = int((datetime.now(timezone.utc) - op_start).total_seconds() * 1000)
            return IngestionResult(
                symbol=symbol,
                granularity=granularity,
                start_time=start_time,
                end_time=end_time,
                candles_fetched=0,
                bars_inserted=0,
                status="error",
                execution_time_ms=duration_ms,
                errors=[str(e)],
            )

    def _candles_to_bars(
        self, candles: List[Candle], symbol: Symbol, symbol_string: Optional[str] = None
    ) -> List[BarData]:
        """Convert exchange candles to storage bars."""
        if not candles:
            return []

        if symbol_string:
            instrument_id = symbol_string.upper()
        else:
            instrument_id = f"{symbol.value}-USD"
            logger.warning(
                f"symbol_string not provided for {symbol}, " f"defaulting to {instrument_id}"
            )

        bars = []
        for candle in candles:
            try:
                bar = BarData(
                    instrument_id=instrument_id,
                    ts=candle.timestamp,
                    o=float(candle.open),
                    h=float(candle.high),
                    l=float(candle.low),
                    c=float(candle.close),
                    volume_base=float(candle.volume),
                    volume_quote=float(candle.volume) * float(candle.close),
                )
                bars.append(bar)
            except Exception as e:
                logger.warning(f"Failed to convert candle for {symbol}: {e}")
                continue

        logger.info(f"Converted {len(bars)}/{len(candles)} candles for {symbol} ({instrument_id})")
        return bars

    def _get_initial_fetch_time(self, granularity: Granularity, end_time: datetime) -> datetime:
        """Get appropriate initial fetch time based on granularity for empty database."""
        if granularity == Granularity.ONE_MINUTE:
            return end_time - timedelta(days=7)
        elif granularity == Granularity.FIVE_MINUTE:
            return end_time - timedelta(days=30)
        elif granularity == Granularity.FIFTEEN_MINUTE:
            return end_time - timedelta(days=60)
        elif granularity == Granularity.ONE_HOUR:
            return end_time - timedelta(days=90)
        elif granularity == Granularity.FOUR_HOUR:
            return end_time - timedelta(days=180)
        elif granularity == Granularity.ONE_DAY:
            return end_time - timedelta(days=365)
        else:
            return end_time - timedelta(days=1)

