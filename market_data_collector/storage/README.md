# SQLite Storage Backend

## Overview

The SQLite storage backend provides per-symbol database management for market data with automatic retention policies and WAL mode enabled for better concurrency.

## Features

- **Per-Symbol Databases**: Each trading symbol gets its own SQLite database file for better isolation and performance
- **WAL Mode**: Write-Ahead Logging enabled for improved concurrency
- **Schema Migrations**: Version-controlled schema with automatic migration support
- **Retention Policy**: Automatic deletion of records older than 7 days on each write operation
- **Bulk Operations**: Efficient bulk insert methods for trades and OHLCV data
- **CCXT-Compatible**: Query methods return data in ccxt-like format

## Usage

### Basic Setup

```python
from market_data_collector.storage import SQLiteStorage

# Create storage for a specific symbol
storage = SQLiteStorage(base_path="data/market_data", symbol="BTCUSDT")
```

### Insert Data

```python
from datetime import datetime

# Insert ticker data
ticker = {
    "timestamp": int(datetime.now().timestamp() * 1000),
    "symbol": "BTCUSDT",
    "bid": 49500.0,
    "ask": 49501.0,
    "last": 49500.0,
    # ... other ticker fields
}
storage.insert_ticker(ticker)

# Insert orderbook snapshot
orderbook = {
    "timestamp": int(datetime.now().timestamp() * 1000),
    "symbol": "BTCUSDT",
    "bids": [[49500.0, 1.5], [49499.0, 2.0]],
    "asks": [[49501.0, 1.2], [49502.0, 1.8]]
}
storage.insert_orderbook(orderbook)

# Bulk insert trades
trades = [
    {
        "id": "trade1",
        "timestamp": int(datetime.now().timestamp() * 1000),
        "symbol": "BTCUSDT",
        "side": "buy",
        "price": 49500.0,
        "amount": 0.5
    },
    # ... more trades
]
inserted_count = storage.insert_trades(trades)

# Bulk insert OHLCV candles
candles = [
    [timestamp, open, high, low, close, volume],
    # ... more candles
]
inserted_count = storage.insert_ohlcv("1m", candles)

# Insert funding rate
funding = {
    "timestamp": int(datetime.now().timestamp() * 1000),
    "symbol": "BTCUSDT",
    "fundingRate": 0.0001
}
storage.insert_funding_rate(funding)

# Insert mark price
mark_price = {
    "timestamp": int(datetime.now().timestamp() * 1000),
    "symbol": "BTCUSDT",
    "markPrice": 49500.0,
    "indexPrice": 49490.0
}
storage.insert_mark_price(mark_price)
```

### Query Data

```python
# Query recent tickers
tickers = storage.query_ticker(limit=100)

# Query tickers within time range
start_time = int(datetime(2024, 1, 1).timestamp() * 1000)
end_time = int(datetime(2024, 1, 2).timestamp() * 1000)
tickers = storage.query_ticker(start_time=start_time, end_time=end_time)

# Query orderbook snapshots
orderbooks = storage.query_orderbook(limit=50)

# Query trades
trades = storage.query_trades(start_time=start_time, end_time=end_time)

# Query OHLCV candles for specific timeframe
candles = storage.query_ohlcv("1m", start_time=start_time, limit=1000)

# Query funding rates
funding_rates = storage.query_funding_rate(limit=24)

# Query mark prices
mark_prices = storage.query_mark_price(limit=100)
```

## Data Schema

### Tables

All tables include timestamp indices for efficient querying and cleanup.

#### ticker
- timestamp (INTEGER, NOT NULL)
- symbol (TEXT, NOT NULL)
- high, low, bid, ask, vwap, open, close, last (REAL)
- bid_volume, ask_volume (REAL)
- previous_close, change, percentage, average (REAL)
- base_volume, quote_volume (REAL)
- info (TEXT)

#### orderbook
- timestamp (INTEGER, NOT NULL)
- symbol (TEXT, NOT NULL)
- bids (TEXT, JSON array)
- asks (TEXT, JSON array)
- nonce (INTEGER)
- datetime (TEXT)

#### trades
- id (TEXT, PRIMARY KEY)
- timestamp (INTEGER, NOT NULL)
- symbol (TEXT, NOT NULL)
- side (TEXT, NOT NULL)
- price (REAL, NOT NULL)
- amount (REAL, NOT NULL)
- cost (REAL)
- order_id (TEXT)
- taker_or_maker (TEXT)
- fee_cost, fee_currency (REAL, TEXT)
- info (TEXT)

#### ohlcv
- timestamp (INTEGER, NOT NULL)
- symbol (TEXT, NOT NULL)
- timeframe (TEXT, NOT NULL)
- open, high, low, close (REAL, NOT NULL)
- volume (REAL, NOT NULL)
- PRIMARY KEY (timestamp, timeframe)

#### funding_rate
- timestamp (INTEGER, PRIMARY KEY)
- symbol (TEXT, NOT NULL)
- funding_rate (REAL, NOT NULL)
- funding_timestamp (INTEGER)
- info (TEXT)

#### mark_price
- timestamp (INTEGER, PRIMARY KEY)
- symbol (TEXT, NOT NULL)
- mark_price (REAL, NOT NULL)
- index_price (REAL)
- info (TEXT)

## Retention Policy

The storage automatically deletes records older than 7 days on each write operation. This ensures:
- Predictable storage usage
- No manual cleanup required
- Recent data always available

To disable retention or adjust the period, modify the `RETENTION_DAYS` constant in `sqlite.py`.

## Database Files

Database files are stored in the base path with sanitized symbol names:
- `BTCUSDT` → `BTCUSDT.db`
- `BTC/USDT:USDT` → `BTC_USDT_USDT.db`

Each database uses WAL mode with accompanying `-wal` and `-shm` files.

## Performance Considerations

- **Bulk Inserts**: Use `insert_trades()` and `insert_ohlcv()` for multiple records
- **Indexes**: All timestamp columns are indexed for fast time-range queries
- **WAL Mode**: Allows concurrent reads while writing
- **Per-Symbol DBs**: Reduces contention and allows parallel processing
- **Retention**: Automatic cleanup keeps database size manageable

## Testing

The storage backend includes comprehensive unit tests covering:
- Schema initialization and migrations
- All data types (ticker, orderbook, trades, OHLCV, funding, mark price)
- Time-range queries
- Retention policy and cleanup
- Per-symbol isolation
- Edge cases and error handling

Run tests with:
```bash
pytest test_sqlite_storage.py -v
```
