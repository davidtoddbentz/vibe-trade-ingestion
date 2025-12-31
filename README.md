# vibe-trade-ingestion

Real-time Coinbase SPOT data ingestion service that fetches 1-minute candles every minute.

## Overview

This service continuously fetches 1-minute OHLCV candles from Coinbase Advanced Trade API and prepares them for publishing to GCP Pub/Sub. The service runs at :05 seconds past each minute to ensure candles are complete.

## Features

- **Real-time Ingestion**: Fetches 1-minute candles every minute
- **CDP API Key Support**: Automatically loads Coinbase CDP API keys from JSON files
- **Multiple Symbols**: Configurable list of trading pairs
- **Cloud Run Ready**: Designed to stay warm and run continuously
- **Graceful Shutdown**: Handles SIGINT/SIGTERM signals properly

## Setup

### Prerequisites

- Python 3.10+
- Coinbase CDP API key file (`cdp_api_key-*.json`)

### Installation

```bash
# Install dependencies
uv sync
```

### Configuration

Place your Coinbase CDP API key file in the project directory:
- File pattern: `cdp_api_key-*.json`
- Or set `COINBASE_CDP_KEY_FILE` environment variable

The JSON file should contain:
```json
{
  "name": "organizations/.../apiKeys/{key_id}",
  "privateKey": "-----BEGIN EC PRIVATE KEY-----\n..."
}
```

### Environment Variables

```bash
# Required: CDP API key file (or use cdp_api_key-*.json in current directory)
COINBASE_CDP_KEY_FILE=/path/to/cdp_api_key.json  # Optional if file is in current dir

# Optional: Use full API key name instead of just key ID
COINBASE_USE_FULL_API_KEY_NAME=false  # Default: false (uses key ID)

# Optional: Coinbase environment
COINBASE_ENVIRONMENT=live  # Default: live (options: sandbox, live)

# Optional: Symbols to fetch
COINBASE_SYMBOLS=BTC-USD,ETH-USD  # Default: BTC-USD,ETH-USD
```

## Usage

```bash
# Run the service
make run

# The service will:
# 1. Load CDP API key from cdp_api_key-*.json
# 2. Start fetching 1-minute candles every minute at :05 seconds
# 3. Log all fetched candles
# 4. Stay running continuously (perfect for Cloud Run)
```

## Architecture

### Project Structure

```
src/
  ├── main.py              # Main entry point with scheduler
  ├── config.py            # Configuration management (CDP keys)
  ├── ingestion/
  │   └── realtime_ingestor.py  # Real-time candle fetcher
  ├── sources/
  │   ├── base.py          # Base exchange adapter
  │   └── coinbase.py      # Coinbase Advanced Trade adapter
  └── models/
      └── candle.py        # Candle data model
```

### How It Works

1. Service starts and calculates next run time (:05 seconds past next minute)
2. Waits until that time
3. Fetches the most recent completed 1-minute candle for each symbol
4. Logs the results
5. Waits for next :05 second mark
6. Repeats

### Future: Pub/Sub Integration

The service is designed to publish candles to GCP Pub/Sub. Currently, candles are logged. The TODO in `main.py` marks where Pub/Sub publishing will be added.

## Development

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

- `coinbase-advanced-py` - Coinbase Advanced Trade API SDK
- `pydantic` - Data validation
- `python-dotenv` - Environment variable management

## License

MIT
