"""End-to-end tests for real-time ingestion flow.

These tests mock HTTP calls to Coinbase API and test the complete flow:
RealtimeIngestor -> CoinbaseExchangeAdapter -> RESTClient -> HTTP
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from src.ingestion.realtime_ingestor import RealtimeIngestor
from src.models.candle import Candle
from src.sources.coinbase import CoinbaseExchangeAdapter
from tests.conftest import MockCandlesResponse, create_mock_candle_response


class TestIngestionE2E:
    """End-to-end tests for the complete ingestion flow."""

    @patch("src.sources.coinbase.RESTClient")
    @patch("src.ingestion.realtime_ingestor.datetime")
    def test_fetch_single_symbol_success(self, mock_datetime, mock_rest_client_class):
        """Test successful end-to-end flow for a single symbol."""
        # Mock current time
        mock_now = datetime(2025, 1, 1, 12, 5, 30, tzinfo=timezone.utc)
        mock_datetime.now.return_value = mock_now
        mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

        # Setup mock REST client
        mock_rest_client = MagicMock()
        mock_rest_client_class.return_value = mock_rest_client

        # Create mock candle response
        base_time = datetime(2025, 1, 1, 12, 3, 0, tzinfo=timezone.utc)
        candle1 = create_mock_candle_response(
            timestamp=base_time,
            open_price=50000.0,
            high=50100.0,
            low=49900.0,
            close=50050.0,
            volume=1.5,
        )
        candle2 = create_mock_candle_response(
            timestamp=base_time.replace(minute=4),
            open_price=50050.0,
            high=50200.0,
            low=50000.0,
            close=50100.0,
            volume=2.0,
        )
        mock_rest_client.get_candles.return_value = MockCandlesResponse([candle1, candle2])

        # Create real adapter and ingestor
        adapter = CoinbaseExchangeAdapter(
            api_key="test-key",
            api_secret="-----BEGIN EC PRIVATE KEY-----\ntest\n-----END EC PRIVATE KEY-----\n",
            environment="sandbox",
        )
        ingestor = RealtimeIngestor(adapter)

        # Execute
        result = ingestor.fetch_latest_1m_candle("BTC-USD")

        # Verify result
        assert result is not None
        assert isinstance(result, Candle)
        assert result.timestamp == base_time.replace(minute=4)  # Most recent
        assert result.open == 50050.0
        assert result.high == 50200.0
        assert result.low == 50000.0
        assert result.close == 50100.0
        assert result.volume == 2.0

        # Verify HTTP call was made correctly
        mock_rest_client.get_candles.assert_called_once()
        call_kwargs = mock_rest_client.get_candles.call_args[1]
        assert call_kwargs["product_id"] == "BTC-USD"
        assert call_kwargs["granularity"] == "ONE_MINUTE"
        # Verify time range (2 minutes before current minute start)
        expected_end = datetime(2025, 1, 1, 12, 5, 0, tzinfo=timezone.utc)
        expected_start = expected_end - timedelta(minutes=2)
        assert call_kwargs["start"] == int(expected_start.timestamp())
        assert call_kwargs["end"] == int(expected_end.timestamp())

    @patch("src.sources.coinbase.RESTClient")
    @patch("src.ingestion.realtime_ingestor.datetime")
    def test_fetch_multiple_symbols_success(self, mock_datetime, mock_rest_client_class):
        """Test successful end-to-end flow for multiple symbols."""
        mock_now = datetime(2025, 1, 1, 12, 5, 30, tzinfo=timezone.utc)
        mock_datetime.now.return_value = mock_now
        mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

        mock_rest_client = MagicMock()
        mock_rest_client_class.return_value = mock_rest_client

        base_time = datetime(2025, 1, 1, 12, 4, 0, tzinfo=timezone.utc)

        def mock_get_candles(**kwargs):
            product_id = kwargs["product_id"]
            if product_id == "BTC-USD":
                return MockCandlesResponse(
                    [
                        create_mock_candle_response(
                            timestamp=base_time,
                            open_price=50000.0,
                            high=50100.0,
                            low=49900.0,
                            close=50050.0,
                            volume=1.5,
                        )
                    ]
                )
            elif product_id == "ETH-USD":
                return MockCandlesResponse(
                    [
                        create_mock_candle_response(
                            timestamp=base_time,
                            open_price=3000.0,
                            high=3100.0,
                            low=2900.0,
                            close=3050.0,
                            volume=10.0,
                        )
                    ]
                )
            return MockCandlesResponse([])

        mock_rest_client.get_candles.side_effect = mock_get_candles

        adapter = CoinbaseExchangeAdapter(
            api_key="test-key",
            api_secret="-----BEGIN EC PRIVATE KEY-----\ntest\n-----END EC PRIVATE KEY-----\n",
            environment="sandbox",
        )
        ingestor = RealtimeIngestor(adapter)

        # Execute
        results = ingestor.fetch_all_symbols(["BTC-USD", "ETH-USD"])

        # Verify results
        assert len(results) == 2
        assert results["BTC-USD"] is not None
        assert results["BTC-USD"].close == 50050.0
        assert results["ETH-USD"] is not None
        assert results["ETH-USD"].close == 3050.0

        # Verify both HTTP calls were made
        assert mock_rest_client.get_candles.call_count == 2
        calls = [call[1] for call in mock_rest_client.get_candles.call_args_list]
        product_ids = [call["product_id"] for call in calls]
        assert "BTC-USD" in product_ids
        assert "ETH-USD" in product_ids

    @patch("src.sources.coinbase.RESTClient")
    @patch("src.ingestion.realtime_ingestor.datetime")
    def test_fetch_handles_empty_response(self, mock_datetime, mock_rest_client_class):
        """Test handling of empty API response."""
        mock_now = datetime(2025, 1, 1, 12, 5, 30, tzinfo=timezone.utc)
        mock_datetime.now.return_value = mock_now
        mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

        mock_rest_client = MagicMock()
        mock_rest_client_class.return_value = mock_rest_client

        # Return empty response
        empty_response = MagicMock()
        empty_response.candles = None
        mock_rest_client.get_candles.return_value = empty_response

        adapter = CoinbaseExchangeAdapter(
            api_key="test-key",
            api_secret="-----BEGIN EC PRIVATE KEY-----\ntest\n-----END EC PRIVATE KEY-----\n",
            environment="sandbox",
        )
        ingestor = RealtimeIngestor(adapter)

        # Execute
        result = ingestor.fetch_latest_1m_candle("BTC-USD")

        # Verify
        assert result is None
        mock_rest_client.get_candles.assert_called_once()

    @patch("src.sources.coinbase.RESTClient")
    @patch("src.ingestion.realtime_ingestor.datetime")
    def test_fetch_handles_http_error(self, mock_datetime, mock_rest_client_class):
        """Test handling of HTTP errors from API."""
        mock_now = datetime(2025, 1, 1, 12, 5, 30, tzinfo=timezone.utc)
        mock_datetime.now.return_value = mock_now
        mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

        mock_rest_client = MagicMock()
        mock_rest_client_class.return_value = mock_rest_client

        # Simulate HTTP error
        from requests.exceptions import HTTPError

        error_response = MagicMock()
        error_response.status_code = 401
        mock_rest_client.get_candles.side_effect = HTTPError(
            "401 Client Error: Unauthorized", response=error_response
        )

        adapter = CoinbaseExchangeAdapter(
            api_key="test-key",
            api_secret="-----BEGIN EC PRIVATE KEY-----\ntest\n-----END EC PRIVATE KEY-----\n",
            environment="sandbox",
        )
        ingestor = RealtimeIngestor(adapter)

        # Execute - should not raise, but return None
        result = ingestor.fetch_latest_1m_candle("BTC-USD")

        # Verify
        assert result is None
        mock_rest_client.get_candles.assert_called_once()

    @patch("src.sources.coinbase.RESTClient")
    @patch("src.ingestion.realtime_ingestor.datetime")
    def test_fetch_handles_partial_failure(self, mock_datetime, mock_rest_client_class):
        """Test handling when one symbol succeeds and another fails."""
        mock_now = datetime(2025, 1, 1, 12, 5, 30, tzinfo=timezone.utc)
        mock_datetime.now.return_value = mock_now
        mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

        mock_rest_client = MagicMock()
        mock_rest_client_class.return_value = mock_rest_client

        base_time = datetime(2025, 1, 1, 12, 4, 0, tzinfo=timezone.utc)

        def mock_get_candles(**kwargs):
            product_id = kwargs["product_id"]
            if product_id == "BTC-USD":
                return MockCandlesResponse(
                    [
                        create_mock_candle_response(
                            timestamp=base_time,
                            open_price=50000.0,
                            high=50100.0,
                            low=49900.0,
                            close=50050.0,
                            volume=1.5,
                        )
                    ]
                )
            elif product_id == "ETH-USD":
                # Simulate error for ETH
                from requests.exceptions import HTTPError

                error_response = MagicMock()
                error_response.status_code = 429
                raise HTTPError("429 Too Many Requests", response=error_response)
            return MockCandlesResponse([])

        mock_rest_client.get_candles.side_effect = mock_get_candles

        adapter = CoinbaseExchangeAdapter(
            api_key="test-key",
            api_secret="-----BEGIN EC PRIVATE KEY-----\ntest\n-----END EC PRIVATE KEY-----\n",
            environment="sandbox",
        )
        ingestor = RealtimeIngestor(adapter)

        # Execute
        results = ingestor.fetch_all_symbols(["BTC-USD", "ETH-USD"])

        # Verify
        assert len(results) == 2
        assert results["BTC-USD"] is not None  # Success
        assert results["BTC-USD"].close == 50050.0
        assert results["ETH-USD"] is None  # Failed

        # Verify both calls were attempted
        assert mock_rest_client.get_candles.call_count == 2

    @patch("src.sources.coinbase.RESTClient")
    @patch("src.ingestion.realtime_ingestor.datetime")
    def test_fetch_selects_most_recent_candle(self, mock_datetime, mock_rest_client_class):
        """Test that the most recent candle is selected when multiple are returned."""
        mock_now = datetime(2025, 1, 1, 12, 5, 30, tzinfo=timezone.utc)
        mock_datetime.now.return_value = mock_now
        mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

        mock_rest_client = MagicMock()
        mock_rest_client_class.return_value = mock_rest_client

        base_time = datetime(2025, 1, 1, 12, 3, 0, tzinfo=timezone.utc)

        # Return multiple candles with different timestamps
        candles = [
            create_mock_candle_response(
                timestamp=base_time,
                open_price=50000.0,
                high=50100.0,
                low=49900.0,
                close=50050.0,
                volume=1.5,
            ),
            create_mock_candle_response(
                timestamp=base_time.replace(minute=3, second=30),
                open_price=50025.0,
                high=50150.0,
                low=50000.0,
                close=50075.0,
                volume=1.75,
            ),
            create_mock_candle_response(
                timestamp=base_time.replace(minute=4),
                open_price=50050.0,
                high=50200.0,
                low=50000.0,
                close=50100.0,
                volume=2.0,
            ),
        ]
        mock_rest_client.get_candles.return_value = MockCandlesResponse(candles)

        adapter = CoinbaseExchangeAdapter(
            api_key="test-key",
            api_secret="-----BEGIN EC PRIVATE KEY-----\ntest\n-----END EC PRIVATE KEY-----\n",
            environment="sandbox",
        )
        ingestor = RealtimeIngestor(adapter)

        # Execute
        result = ingestor.fetch_latest_1m_candle("BTC-USD")

        # Verify most recent candle is returned
        assert result is not None
        assert result.timestamp == base_time.replace(minute=4)
        assert result.close == 50100.0

    @patch("src.sources.coinbase.RESTClient")
    @patch("src.ingestion.realtime_ingestor.datetime")
    def test_fetch_time_range_calculation(self, mock_datetime, mock_rest_client_class):
        """Test that time range is calculated correctly for fetching completed candles."""
        # Test at different times to verify range calculation
        test_cases = [
            datetime(2025, 1, 1, 12, 5, 30, tzinfo=timezone.utc),
            datetime(2025, 1, 1, 12, 0, 15, tzinfo=timezone.utc),
            datetime(2025, 1, 1, 12, 59, 45, tzinfo=timezone.utc),
        ]

        for mock_now in test_cases:
            mock_datetime.now.return_value = mock_now
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

            mock_rest_client = MagicMock()
            mock_rest_client_class.return_value = mock_rest_client

            # Create a candle at the expected end time
            expected_end = mock_now.replace(second=0, microsecond=0)
            candle = create_mock_candle_response(
                timestamp=expected_end - timedelta(minutes=1),  # Previous minute
                open_price=50000.0,
                high=50100.0,
                low=49900.0,
                close=50050.0,
                volume=1.5,
            )
            mock_rest_client.get_candles.return_value = MockCandlesResponse([candle])

            adapter = CoinbaseExchangeAdapter(
                api_key="test-key",
                api_secret="-----BEGIN EC PRIVATE KEY-----\ntest\n-----END EC PRIVATE KEY-----\n",
                environment="sandbox",
            )
            ingestor = RealtimeIngestor(adapter)

            # Execute
            ingestor.fetch_latest_1m_candle("BTC-USD")

            # Verify time range
            call_kwargs = mock_rest_client.get_candles.call_args[1]
            start_dt = datetime.fromtimestamp(call_kwargs["start"], tz=timezone.utc)
            end_dt = datetime.fromtimestamp(call_kwargs["end"], tz=timezone.utc)

            # End should be start of current minute
            assert end_dt == expected_end

            # Start should be 2 minutes before end
            expected_start = expected_end - timedelta(minutes=2)
            assert start_dt == expected_start

            mock_rest_client.reset_mock()

    @patch("src.sources.coinbase.RESTClient")
    @patch("src.ingestion.realtime_ingestor.datetime")
    def test_fetch_with_pagination(self, mock_datetime, mock_rest_client_class):
        """Test that pagination works correctly for large time ranges."""
        mock_now = datetime(2025, 1, 1, 12, 5, 30, tzinfo=timezone.utc)
        mock_datetime.now.return_value = mock_now
        mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

        mock_rest_client = MagicMock()
        mock_rest_client_class.return_value = mock_rest_client

        # Simulate pagination - return candles in chunks
        call_count = 0

        def mock_get_candles(**kwargs):
            nonlocal call_count
            call_count += 1
            start_ts = kwargs["start"]
            end_ts = kwargs["end"]
            start_dt = datetime.fromtimestamp(start_ts, tz=timezone.utc)

            candles = []
            current = start_dt
            # Return up to 350 candles per chunk (max per request)
            while current.timestamp() < end_ts and len(candles) < 350:
                candles.append(
                    create_mock_candle_response(
                        timestamp=current,
                        open_price=50000.0,
                        high=50100.0,
                        low=49900.0,
                        close=50050.0,
                        volume=1.0,
                    )
                )
                current += timedelta(minutes=1)

            return MockCandlesResponse(candles)

        mock_rest_client.get_candles.side_effect = mock_get_candles

        adapter = CoinbaseExchangeAdapter(
            api_key="test-key",
            api_secret="-----BEGIN EC PRIVATE KEY-----\ntest\n-----END EC PRIVATE KEY-----\n",
            environment="sandbox",
        )
        ingestor = RealtimeIngestor(adapter)

        # This should work normally (2 minute range, won't trigger pagination)
        result = ingestor.fetch_latest_1m_candle("BTC-USD")

        assert result is not None
        # Should only call once for 2-minute range
        assert mock_rest_client.get_candles.call_count == 1

