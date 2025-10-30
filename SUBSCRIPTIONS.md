# Data Subscriptions Module

## Overview

The subscription system provides async tasks for continuous market data collection using `ccxt.pro` WebSocket APIs. Each subscription type runs independently per symbol with throttling, reconnection logic, and data normalization.

## Features

### Supported Data Types

1. **Ticker** - Real-time price updates
   - Best bid/ask prices
   - Last trade price
   - 24h volume and changes
   - Configurable throttling interval

2. **Order Book** - Market depth snapshots
   - Configurable depth (number of price levels)
   - Bid and ask levels
   - Throttled snapshots at intervals

3. **Trades** - Individual trade events
   - Trade price, amount, side (buy/sell)
   - Trade timestamps
   - Real-time or throttled updates

4. **OHLCV** - Candlestick/kline data
   - **Multiple timeframes** (1m, 5m, 15m, 1h, etc.)
   - Open, High, Low, Close, Volume
   - Independent subscriptions per timeframe

5. **Funding Rate** - Perpetual futures funding
   - Current funding rate
   - Next funding time
   - Typically updated every 8 hours

6. **Mark Price** - Liquidation reference price
   - Fair price for liquidations
   - Derived from index/ticker
   - Configurable update interval

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    SubscriptionManager                       │
├─────────────────────────────────────────────────────────────┤
│  • Manages lifecycle of all subscriptions                   │
│  • Creates async tasks per symbol × data type               │
│  • Provides data queues for storage pipeline                │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│   Symbol 1   │      │   Symbol 2   │      │   Symbol 3   │
├──────────────┤      ├──────────────┤      ├──────────────┤
│ • Ticker     │      │ • Ticker     │      │ • Ticker     │
│ • Orderbook  │      │ • Orderbook  │      │ • Orderbook  │
│ • Trades     │      │ • Trades     │      │ • Trades     │
│ • OHLCV 1m   │      │ • OHLCV 1m   │      │ • OHLCV 1m   │
│ • OHLCV 5m   │      │ • OHLCV 5m   │      │ • OHLCV 5m   │
│ • OHLCV 1h   │      │ • OHLCV 1h   │      │ • OHLCV 1h   │
│ • Funding    │      │ • Funding    │      │ • Funding    │
│ • Mark Price │      │ • Mark Price │      │ • Mark Price │
└──────────────┘      └──────────────┘      └──────────────┘
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                              ▼
                    ┌──────────────────┐
                    │  Data Queues     │
                    ├──────────────────┤
                    │ • ticker_queue   │
                    │ • orderbook_queue│
                    │ • trades_queue   │
                    │ • ohlcv_queue    │
                    │ • funding_queue  │
                    │ • mark_price_queue│
                    └──────────────────┘
                              ▼
                    ┌──────────────────┐
                    │ Storage Writers  │
                    │  (SQLite, etc.)  │
                    └──────────────────┘
```

## Configuration

### Config File (`market.yaml`)

```yaml
exchange:
  name: Bybit
  market_type: usdt_perpetual
  base_rest_url: https://api.bybit.com
  base_websocket_url: wss://stream.bybit.com/v5/public/linear

symbols:
  - BTCUSDT
  - ETHUSDT
  - SOLUSDT

intervals:
  klines: 1m,5m,15m,1h  # Multiple OHLCV timeframes (comma-separated)
  orderbook_snapshot: 1m  # Orderbook update interval
  trades: realtime  # Trades (realtime or throttled)
  funding: 8h  # Funding rate check interval
  mark_price: 1m  # Mark price update interval

orderbook:
  depth: 200  # Number of price levels
```

### Interval Formats

- `realtime` - No throttling, continuous updates
- `Ns` - N seconds (e.g., `30s`)
- `Nm` - N minutes (e.g., `1m`, `5m`)
- `Nh` - N hours (e.g., `1h`, `8h`)

## Usage

### Basic Usage

```python
import asyncio
from market_data_collector import (
    ExchangeAdapter,
    SubscriptionManager,
    settings,
)

async def main():
    # Create exchange adapter
    exchange = ExchangeAdapter(
        exchange_name="bybit",
        default_type="swap",
    )
    
    # Create subscription manager
    sub_manager = SubscriptionManager(exchange, settings)
    
    # Start subscriptions
    await sub_manager.start()
    
    # Consume data from queues
    while True:
        # Get ticker data
        if not sub_manager.ticker_queue.empty():
            data = await sub_manager.ticker_queue.get()
            print(f"Ticker: {data['symbol']} - ${data['data']['last']}")
            sub_manager.ticker_queue.task_done()
        
        await asyncio.sleep(0.1)
    
    # Stop subscriptions
    await sub_manager.stop()
    
    # Close exchange
    await exchange.close()

asyncio.run(main())
```

### With Runtime Integration

```python
from market_data_collector import runtime, SubscriptionManager

# Register subscription manager with runtime
exchange = ExchangeAdapter("bybit", "swap")
sub_manager = SubscriptionManager(exchange, settings)

runtime.register_collector(
    "subscriptions",
    start=lambda: asyncio.create_task(sub_manager.start()),
    stop=lambda: asyncio.create_task(sub_manager.stop()),
)

# Runtime will manage lifecycle
runtime.start()
```

### Example Script

Run the example demonstration:

```bash
# From project root
python examples/run_subscriptions.py
```

This script:
- Starts subscriptions for all configured symbols
- Creates consumers for each data queue
- Logs received data
- Handles graceful shutdown (Ctrl+C)

## Data Queue Format

Each queue receives data in a standardized format:

### Ticker Queue

```python
{
    "type": "ticker",
    "symbol": "BTC/USDT:USDT",
    "data": {
        "symbol": "BTC/USDT:USDT",
        "timestamp": 1698765432000,  # milliseconds
        "last": 35000.0,
        "bid": 34999.5,
        "ask": 35000.5,
        "high": 35500.0,
        "low": 34500.0,
        "volume": 12345.67,
        # ... more ticker fields
    }
}
```

### Orderbook Queue

```python
{
    "type": "orderbook",
    "symbol": "BTC/USDT:USDT",
    "data": {
        "symbol": "BTC/USDT:USDT",
        "timestamp": 1698765432000,
        "bids": [
            [34999.5, 1.5],  # [price, amount]
            [34999.0, 2.3],
            # ...
        ],
        "asks": [
            [35000.5, 1.8],
            [35001.0, 2.1],
            # ...
        ],
        # ... more orderbook fields
    }
}
```

### Trades Queue

```python
{
    "type": "trade",
    "symbol": "BTC/USDT:USDT",
    "data": {
        "id": "12345678",
        "timestamp": 1698765432000,
        "symbol": "BTC/USDT:USDT",
        "side": "buy",  # or "sell"
        "price": 35000.0,
        "amount": 0.5,
        # ... more trade fields
    }
}
```

### OHLCV Queue

```python
{
    "type": "ohlcv",
    "symbol": "BTC/USDT:USDT",
    "timeframe": "1m",  # or "5m", "1h", etc.
    "data": [
        1698765420000,  # timestamp (ms)
        34990.0,  # open
        35010.0,  # high
        34980.0,  # low
        35000.0,  # close
        123.45,   # volume
    ]
}
```

### Funding Rate Queue

```python
{
    "type": "funding_rate",
    "symbol": "BTC/USDT:USDT",
    "data": {
        "symbol": "BTC/USDT:USDT",
        "fundingRate": 0.0001,
        "fundingTimestamp": 1698768000000,
        "timestamp": 1698765432000,
        # ... more funding fields
    }
}
```

### Mark Price Queue

```python
{
    "type": "mark_price",
    "symbol": "BTC/USDT:USDT",
    "data": {
        "symbol": "BTC/USDT:USDT",
        "mark_price": 35005.5,
        "timestamp": 1698765432000,
    }
}
```

## Throttling and Intervals

### How Throttling Works

Each subscription respects its configured interval:

1. **Realtime** (`interval=None`):
   - Continuous updates as data arrives
   - No artificial delays
   - Best for trades stream

2. **Throttled** (e.g., `interval=60`):
   - Fetch data
   - Wait for interval duration
   - Repeat
   - Best for snapshots (orderbook, funding)

### OHLCV Multiple Timeframes

OHLCV subscriptions support multiple timeframes independently:

```yaml
intervals:
  klines: 1m,5m,15m,1h,4h,1d
```

This creates **separate subscriptions** for each timeframe per symbol:
- `BTC/USDT:USDT` @ 1m
- `BTC/USDT:USDT` @ 5m
- `BTC/USDT:USDT` @ 15m
- etc.

Each timeframe runs independently with its own throttling.

## Reconnection and Error Handling

### Automatic Reconnection

The `ExchangeAdapter` provides automatic reconnection with exponential backoff:

- **Max retries**: 5 attempts
- **Base backoff**: 1 second
- **Max backoff**: 60 seconds
- **Backoff strategy**: Exponential (1s, 2s, 4s, 8s, 16s, ...)

### Error Recovery

Each subscription task has its own error recovery:

1. **Network errors**: Automatic retry with backoff
2. **Rate limits**: Handled by ccxt's rate limiting
3. **Invalid data**: Logged and skipped
4. **Fatal errors**: Task stops, logged for investigation

### Graceful Shutdown

Subscriptions support graceful shutdown:

```python
# Stop all subscriptions
await sub_manager.stop()

# All tasks cancelled cleanly
# Queues can be drained
# No data loss
```

## Monitoring

### Queue Sizes

Monitor queue health:

```python
sizes = sub_manager.get_queue_sizes()
# {'ticker': 0, 'orderbook': 5, 'trades': 120, ...}
```

### Task Status

Check active tasks:

```python
print(f"Active tasks: {sub_manager.task_count}")
print(f"Running: {sub_manager.is_running}")
```

### Logging

Subscriptions use Python logging:

```python
import logging

# Set log level
logging.getLogger("market_data_collector.subscriptions").setLevel(logging.DEBUG)

# Log messages include:
# - Subscription start/stop
# - Data received (debug level)
# - Errors and retries
# - Task status
```

## Performance Considerations

### Queue Sizes

Default queue sizes:
- Ticker: 1000 items
- Orderbook: 1000 items
- Trades: 1000 items (can grow quickly!)
- OHLCV: 1000 items
- Funding: 100 items
- Mark Price: 1000 items

Adjust based on:
- Consumer speed
- Data rate
- Memory constraints

### Backpressure

If queues fill up:
- Subscriptions will block on `queue.put()`
- Consumers must keep up with data rate
- Consider increasing consumer workers

### Concurrent Subscriptions

Total tasks = symbols × enabled_subscriptions

Example:
- 10 symbols
- 6 data types (ticker, orderbook, trades, funding, mark_price)
- 4 OHLCV timeframes
- **Total**: 10 × (5 + 4) = 90 async tasks

This is efficient with asyncio but monitor:
- WebSocket connections
- Memory usage
- Exchange rate limits

## Best Practices

1. **Configure intervals wisely**:
   - Use realtime only where needed (trades)
   - Throttle snapshots (orderbook, funding)
   - Balance data freshness vs. load

2. **Multiple timeframes**:
   - Only subscribe to timeframes you need
   - Higher timeframes = less data volume

3. **Monitor queues**:
   - Check queue sizes regularly
   - Ensure consumers keep up
   - Alert on queue buildup

4. **Graceful shutdown**:
   - Always call `stop()` before exit
   - Drain queues before closing
   - Log any dropped data

5. **Error handling**:
   - Monitor logs for repeated errors
   - Investigate reconnection patterns
   - Consider exchange-specific quirks

## Integration with Storage

The subscription queues feed into storage writers:

```python
async def storage_writer(queue: asyncio.Queue, storage: SQLiteStorage):
    """Write data from queue to storage."""
    while True:
        data = await queue.get()
        
        try:
            # Write to storage based on type
            if data["type"] == "ticker":
                await storage.write_ticker(data["symbol"], data["data"])
            elif data["type"] == "orderbook":
                await storage.write_orderbook(data["symbol"], data["data"])
            # ... etc
            
            queue.task_done()
        except Exception as e:
            logger.error(f"Storage write error: {e}")
```

See `storage/` module for storage implementations.

## Troubleshooting

### Subscriptions not starting

- Check config: symbols and intervals must be defined
- Verify exchange connectivity
- Check logs for initialization errors

### No data in queues

- Verify subscriptions started: `sub_manager.is_running`
- Check task count: `sub_manager.task_count`
- Look for errors in logs
- Test exchange connectivity manually

### Queue overflow

- Increase queue sizes in `SubscriptionManager.__init__`
- Add more consumer workers
- Increase consumer processing speed
- Reduce subscription intervals

### High memory usage

- Too many subscriptions?
- Queues too large?
- Consumers not draining queues?
- Check for memory leaks in consumers

### Frequent reconnections

- Network issues?
- Exchange rate limiting?
- Check backoff logs
- Verify exchange status page

## Testing

Run the example script to test subscriptions:

```bash
# Basic test
python examples/run_subscriptions.py

# With custom config
MARKET_DATA_CONFIG_PATH=custom.yaml python examples/run_subscriptions.py

# Test specific exchange
MARKET_DATA__EXCHANGE__NAME=binance python examples/run_subscriptions.py
```

## Future Enhancements

Potential improvements:

1. **Dynamic subscription management**: Add/remove symbols at runtime
2. **Backfill support**: Fetch historical data on startup
3. **Data persistence**: Direct write to storage (skip queues)
4. **Metrics**: Prometheus metrics for monitoring
5. **Health checks**: Automatic subscription recovery
6. **Multiplexing**: Share WebSocket connections across symbols
7. **Compression**: Compress queue data to save memory
8. **Priority queues**: Different priorities for data types

## References

- [ccxt.pro Documentation](https://github.com/ccxt/ccxt/wiki/ccxt.pro)
- [Bybit WebSocket API](https://bybit-exchange.github.io/docs/v5/ws/connect)
- [Exchange Adapter Documentation](EXCHANGE_ADAPTER.md)
- [Storage Implementation](SQLITE_STORAGE_IMPLEMENTATION.md)
