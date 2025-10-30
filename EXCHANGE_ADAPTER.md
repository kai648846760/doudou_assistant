# Exchange Adapter Implementation

## Overview

The exchange adapter provides a unified interface for connecting to cryptocurrency exchanges using both WebSocket (via `ccxt.pro`) and REST (via `ccxt`) protocols. It's specifically configured for Bybit swap (perpetual futures) markets with support for testnet/sandbox mode.

## Features

### 1. Dual Protocol Support
- **WebSocket (ccxt.pro)**: Real-time data streaming for tickers, order books, trades, and OHLCV
- **REST (ccxt)**: Fallback methods for on-demand data fetching

### 2. Configuration
- **Exchange**: Bybit
- **Market Type**: swap (USDT perpetual futures)
- **Sandbox Mode**: Configurable for testing (connects to testnet)
- **Rate Limiting**: Enabled by default

### 3. Async Watchers (WebSocket)
- `watch_ticker(symbol)` - Real-time ticker updates
- `watch_order_book(symbol, limit)` - Order book streaming
- `watch_trades(symbol)` - Trade feed
- `watch_ohlcv(symbol, timeframe)` - Candlestick data

### 4. REST Fallback Methods
- `fetch_ticker(symbol)` - Snapshot ticker data
- `fetch_order_book(symbol, limit)` - Snapshot order book
- `fetch_trades(symbol, since, limit)` - Historical trades
- `fetch_ohlcv(symbol, timeframe, since, limit)` - Historical OHLCV

### 5. Perpetual Futures Specific
- `fetch_funding_rate(symbol)` - Current funding rate
- `fetch_funding_rate_history(symbol, since, limit)` - Historical funding rates
- `derive_mark_price(symbol)` - Mark price for liquidations

### 6. Reliability Features
- **Reconnection Logic**: Automatic reconnection on connection failures
- **Exponential Backoff**: 1s to 60s backoff with max 5 retries
- **Timestamp Normalization**: All timestamps converted to milliseconds
- **Resource Management**: Context manager support for proper cleanup

## Usage

### Basic Initialization

```python
from market_data_collector import create_exchange_adapter

# Production
adapter = create_exchange_adapter(
    exchange_name="bybit",
    default_type="swap",
    sandbox=False,
)

# Testnet/Sandbox
adapter = create_exchange_adapter(
    exchange_name="bybit",
    default_type="swap",
    sandbox=True,
)
```

### Context Manager (Recommended)

```python
async with create_exchange_adapter("bybit", "swap", sandbox=True) as adapter:
    # Use adapter
    ticker = await adapter.watch_ticker("BTC/USDT:USDT")
    print(f"Price: {ticker['last']}")
# Automatically cleaned up
```

### WebSocket Streaming

```python
async def stream_ticker():
    adapter = create_exchange_adapter("bybit", "swap", sandbox=True)
    
    try:
        while True:
            ticker = await adapter.watch_ticker("BTC/USDT:USDT")
            print(f"BTC Price: {ticker['last']}, Timestamp: {ticker['timestamp']} ms")
    finally:
        await adapter.close()
```

### REST Fallback

```python
async def fetch_historical_data():
    adapter = create_exchange_adapter("bybit", "swap", sandbox=True)
    
    try:
        # Fetch last 100 candles
        ohlcv = await adapter.fetch_ohlcv(
            symbol="BTC/USDT:USDT",
            timeframe="1h",
            limit=100
        )
        
        for candle in ohlcv:
            timestamp, open, high, low, close, volume = candle
            print(f"Timestamp: {timestamp} ms, Close: {close}")
    finally:
        await adapter.close()
```

### Funding Rates

```python
async def check_funding():
    adapter = create_exchange_adapter("bybit", "swap", sandbox=True)
    
    try:
        # Current funding rate
        funding = await adapter.fetch_funding_rate("BTC/USDT:USDT")
        print(f"Funding Rate: {funding['fundingRate']}")
        
        # Mark price
        mark_price = await adapter.derive_mark_price("BTC/USDT:USDT")
        print(f"Mark Price: {mark_price}")
    finally:
        await adapter.close()
```

### Symbol Formatting

```python
adapter = create_exchange_adapter("bybit", "swap")

# Perpetual futures (swap)
symbol = adapter.get_market_symbol("BTC", "USDT")
# Returns: "BTC/USDT:USDT"

# Spot (if configured with default_type="spot")
adapter_spot = create_exchange_adapter("bybit", "spot")
symbol = adapter_spot.get_market_symbol("BTC", "USDT")
# Returns: "BTC/USDT"
```

## Data Format

### Timestamps
All timestamps are normalized to **milliseconds** (not seconds).

```python
ticker = await adapter.watch_ticker("BTC/USDT:USDT")
# ticker['timestamp'] is in milliseconds
```

### Ticker Structure

```python
{
    'symbol': 'BTC/USDT:USDT',
    'timestamp': 1609459200000,  # milliseconds
    'datetime': '2021-01-01T00:00:00.000Z',
    'last': 50000.0,
    'bid': 49999.0,
    'ask': 50001.0,
    'baseVolume': 1234.56,
    'quoteVolume': 61728000.0,
    'info': { ... }  # raw exchange data
}
```

### Order Book Structure

```python
{
    'symbol': 'BTC/USDT:USDT',
    'timestamp': 1609459200000,
    'bids': [[49999.0, 1.5], [49998.0, 2.0], ...],  # [price, amount]
    'asks': [[50001.0, 1.2], [50002.0, 1.8], ...],
    'nonce': 12345
}
```

### OHLCV Structure

```python
[
    [1609459200000, 50000.0, 51000.0, 49000.0, 50500.0, 100.0],  
    # [timestamp_ms, open, high, low, close, volume]
    ...
]
```

## Error Handling

The adapter implements automatic retry with exponential backoff:

```python
# Automatic retry on failure
try:
    ticker = await adapter.watch_ticker("BTC/USDT:USDT")
except Exception as e:
    # Only raised after 5 failed attempts
    print(f"Failed after retries: {e}")
```

Retry parameters:
- **max_retries**: 5 attempts
- **base_backoff**: 1.0 seconds
- **max_backoff**: 60.0 seconds
- Backoff formula: `min(base_backoff * (2 ** attempt), max_backoff)`

## Testing

### Dry-Run Test (No Network)

```bash
uv run python test_exchange_dry_run.py
```

Tests:
- ✓ Adapter initialization
- ✓ Timestamp normalization
- ✓ Symbol formatting
- ✓ Exchange instance creation
- ✓ Configuration validation

### Acceptance Test (Network Required)

```bash
uv run python test_exchange_adapter.py
```

Tests (using Bybit testnet):
- ✓ WebSocket connection and data reception
- ✓ REST API fallback
- ✓ Funding rate and mark price retrieval
- ✓ Reconnection logic

## Integration with Market Data Collector

The exchange adapter is designed to work with the market data collector runtime:

```python
from market_data_collector import create_exchange_adapter, get_runtime

async def collect_data():
    runtime = get_runtime()
    adapter = create_exchange_adapter("bybit", "swap", sandbox=False)
    
    try:
        runtime.start()
        
        # Stream data
        while not runtime.stop_event.is_set():
            ticker = await adapter.watch_ticker("BTC/USDT:USDT")
            # Process and store ticker data
            
    finally:
        await adapter.close()
        runtime.stop()
```

## Configuration via YAML

The adapter can be configured via `market_data_collector/configs/market.yaml`:

```yaml
exchange:
  name: Bybit
  market_type: usdt_perpetual
  base_rest_url: https://api.bybit.com
  base_websocket_url: wss://stream.bybit.com/v5/public/linear

runtime:
  dry_run: false
  sandbox: false  # Set to true for testnet
```

Override via environment variables:

```bash
export MARKET_DATA_EXCHANGE__NAME="bybit"
export MARKET_DATA_RUNTIME__SANDBOX="true"
```

## Production Considerations

### 1. API Keys
For private endpoints (orders, positions):

```python
adapter = create_exchange_adapter(
    exchange_name="bybit",
    default_type="swap",
    sandbox=False,
    api_key="your_api_key",
    secret="your_secret"
)
```

### 2. Rate Limiting
Always keep `enableRateLimit=True` to avoid being banned.

### 3. Error Monitoring
Log all exceptions for production monitoring:

```python
import logging
logger = logging.getLogger("market_data")

try:
    ticker = await adapter.watch_ticker(symbol)
except Exception as e:
    logger.error(f"Failed to watch ticker: {e}", exc_info=True)
```

### 4. Resource Cleanup
Always use context managers or explicit cleanup:

```python
# Context manager (preferred)
async with create_exchange_adapter(...) as adapter:
    pass

# Explicit cleanup
adapter = create_exchange_adapter(...)
try:
    pass
finally:
    await adapter.close()
```

## Limitations

1. **WebSocket Stability**: Long-running WebSocket connections may disconnect. The retry logic handles reconnections.
2. **Testnet Differences**: Sandbox/testnet data may differ from production (different liquidity, prices).
3. **Symbol Format**: Perpetual futures use format `BASE/QUOTE:SETTLE` (e.g., `BTC/USDT:USDT`).

## Troubleshooting

### "Exchange not found" error
Ensure `ccxt` and `ccxt.pro` are installed:
```bash
uv sync
```

### "Invalid symbol" error
Check symbol format for swap markets:
```python
# Correct for swap
symbol = "BTC/USDT:USDT"

# Incorrect
symbol = "BTCUSDT"
```

### Connection timeout
Enable sandbox mode for testing:
```python
adapter = create_exchange_adapter("bybit", "swap", sandbox=True)
```

### WebSocket disconnects
The adapter automatically reconnects with exponential backoff. Check logs for retry attempts.

## References

- [CCXT Documentation](https://docs.ccxt.com/)
- [CCXT.Pro Documentation](https://docs.ccxt.com/en/latest/ccxt.pro.html)
- [Bybit API Documentation](https://bybit-exchange.github.io/docs/)
