# vibe-trade-ingestion

Data ingestion service for spot market data into ClickHouse database.

## Overview

This service ingests OHLCV (Open, High, Low, Close, Volume) candle data from various exchanges and stores it in ClickHouse for efficient querying and analysis.

## Features

- **Spot Data Ingestion**: Ingest OHLCV candles from multiple exchanges
- **ClickHouse Storage**: Efficient time-series storage with partitioning
- **Batch Processing**: Insert multiple candles in a single batch
- **Resume Support**: Track latest timestamps to resume ingestion from last point
- **Multiple Modes**: Append latest, backfill by days, or ingest specific time ranges
- **Gap Detection**: Automatically detects and handles data gaps

## Setup

### Prerequisites

- Python 3.10+
- ClickHouse server (local or remote)
- Coinbase API credentials (for Coinbase data)

### Installation

```bash
# Install dependencies
uv sync

# Or with pip
pip install -e .
```

### Environment Variables

Create a `.env` file:

```bash
# ClickHouse Configuration
CLICKHOUSE_HOST=localhost
CLICKHOUSE_PORT=8123
CLICKHOUSE_USERNAME=default
CLICKHOUSE_PASSWORD=
CLICKHOUSE_DATABASE=default

# Coinbase API (required)
COINBASE_API_KEY=your_api_key
COINBASE_API_SECRET=your_api_secret
COINBASE_ENVIRONMENT=sandbox  # or "live"

# Ingestion Configuration
INGESTION_SYMBOLS=BTC-USD,ETH-USD,SOL-USD  # Comma-separated list
INGESTION_GRANULARITY=1m  # 1m, 5m, 15m, 1h, 4h, 1d

# Optional: Time Range Parameters (mutually exclusive)
# Option 1: Backfill specific number of days
INGESTION_DAYS=7

# Option 2: Specify exact time range (both required)
INGESTION_START_TIME=2025-01-20T00:00:00Z
INGESTION_END_TIME=2025-01-27T00:00:00Z

# Scheduler Configuration (for scheduler.py)
INGESTION_INTERVAL_MINUTES=1  # Minutes between runs
```

## Usage

### Quick Start

```bash
# Setup ClickHouse, initialize tables, and run ingestion (all-in-one)
make run

# This will:
# 1. Setup ClickHouse in Docker (if not already running)
# 2. Initialize all required database tables
# 3. Run the batch ingestion job
```

### ClickHouse Setup

```bash
# Setup ClickHouse in Docker
make setup-clickhouse

# Initialize database tables
make init-db

# Check ClickHouse status
make clickhouse-status

# Stop ClickHouse
make clickhouse-stop
```

### Run Once (Batch Job)

```bash
# Run ingestion once (assumes ClickHouse is already running)
make batch-job

# Or directly
uv run python batch_job.py
```

### Run Periodically (Scheduler)

```bash
# Run scheduler (runs batch job every N minutes)
make scheduler

# Or directly
uv run python scheduler.py
```

### Ingestion Modes

The batch job supports three ingestion modes:

1. **Append Latest (Default)**: Fetches the latest data since the last ingestion
   ```bash
   python batch_job.py
   ```

2. **Backfill by Days**: Fetches data for the last N days
   ```bash
   INGESTION_DAYS=30 python batch_job.py
   ```

3. **Time Range**: Fetches data for a specific time range
   ```bash
   INGESTION_START_TIME=2025-01-20T00:00:00Z \
   INGESTION_END_TIME=2025-01-27T00:00:00Z \
   python batch_job.py
   ```

## Architecture

### Database Schema

The service creates tables for different granularities:

- `bars_1m_spot`: 1-minute spot price bars
- `bars_5m_spot`: 5-minute spot price bars
- `bars_15m_spot`: 15-minute spot price bars
- `bars_1h_spot`: 1-hour spot price bars
- `bars_4h_spot`: 4-hour spot price bars
- `bars_1d_spot`: 1-day spot price bars

Each table has the following schema:

- `ts`: DateTime (UTC) - Candle timestamp
- `instrument_id`: String - Trading pair (e.g., 'BTC-USD')
- `o`: Float64 - Open price
- `h`: Float64 - High price
- `l`: Float64 - Low price
- `c`: Float64 - Close price
- `volume_base`: Float64 - Base volume
- `volume_quote`: Float64 - Quote volume

Tables are partitioned by month and ordered by (instrument_id, ts) for efficient queries.

### Project Structure

```
src/
  ├── models/          # Data models (Candle, BarData, Results)
  ├── sources/         # Exchange adapters (Coinbase, etc.)
  ├── db/              # ClickHouse client
  ├── ingestion/       # Ingestion logic (SpotIngestor, StorageService)
  └── config.py        # Configuration management
batch_job.py           # Entry point for batch jobs
scheduler.py            # Periodic scheduler
```

## Development

### Adding New Exchanges

Create a new exchange adapter by extending `ExchangeAdapter`:

```python
from src.sources.base import ExchangeAdapter, Symbol, Granularity
from src.models.candle import Candle

class MyExchangeAdapter(ExchangeAdapter):
    def get_candles(self, symbol, symbol_string, start_time, end_time, granularity, limit=None):
        # Implement fetching logic
        return [Candle(...), ...]
```

### Testing

```bash
# Run tests
make test

# With coverage
make test-cov
```

### Linting and Formatting

```bash
# Lint
make lint

# Format
make format

# Both
make check
```

## Dependencies

- `clickhouse-connect` - ClickHouse Python client
- `coinbase-advanced-py` - Coinbase Advanced Trade API SDK
- `pydantic` - Data validation
- `httpx` - HTTP client for API requests
- `python-dotenv` - Environment variable management

## License

MIT
