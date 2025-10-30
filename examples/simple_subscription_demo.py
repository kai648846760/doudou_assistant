#!/usr/bin/env python3
"""
Simple demonstration of subscription system with mock exchange.

This example shows how subscriptions work with mocked data, without
requiring actual exchange connectivity.
"""

import asyncio
import logging
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from market_data_collector import SubscriptionManager
from market_data_collector.config import MarketDataSettings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def create_mock_exchange():
    """Create a mock exchange that returns sample data."""
    exchange = MagicMock()
    
    # Mock ticker data
    exchange.watch_ticker = AsyncMock(return_value={
        "symbol": "BTC/USDT:USDT",
        "timestamp": 1698765432000,
        "last": 35000.0,
        "bid": 34999.5,
        "ask": 35000.5,
        "high": 35500.0,
        "low": 34500.0,
        "volume": 12345.67,
    })
    
    # Mock orderbook data
    exchange.watch_order_book = AsyncMock(return_value={
        "symbol": "BTC/USDT:USDT",
        "timestamp": 1698765432000,
        "bids": [
            [34999.5, 1.5],
            [34999.0, 2.3],
            [34998.5, 3.1],
        ],
        "asks": [
            [35000.5, 1.8],
            [35001.0, 2.1],
            [35001.5, 2.9],
        ],
    })
    
    # Mock trades data
    exchange.watch_trades = AsyncMock(return_value=[
        {
            "id": "12345",
            "timestamp": 1698765432000,
            "symbol": "BTC/USDT:USDT",
            "side": "buy",
            "price": 35000.0,
            "amount": 0.5,
        }
    ])
    
    # Mock OHLCV data
    exchange.watch_ohlcv = AsyncMock(return_value=[
        [1698765420000, 34990.0, 35010.0, 34980.0, 35000.0, 123.45]
    ])
    
    # Mock funding rate
    exchange.fetch_funding_rate = AsyncMock(return_value={
        "symbol": "BTC/USDT:USDT",
        "fundingRate": 0.0001,
        "fundingTimestamp": 1698768000000,
        "timestamp": 1698765432000,
    })
    
    # Mock mark price
    exchange.derive_mark_price = AsyncMock(return_value=35005.5)
    
    return exchange


async def main():
    """Main demo function."""
    logger.info("=" * 60)
    logger.info("Simple Subscription Demo (Mock Exchange)")
    logger.info("=" * 60)
    
    # Create mock settings
    settings = MarketDataSettings.model_validate({
        "exchange": {
            "name": "Bybit",
            "market_type": "usdt_perpetual",
            "base_rest_url": "https://api.bybit.com",
            "base_websocket_url": "wss://stream.bybit.com/v5/public/linear",
        },
        "symbols": ["BTC/USDT:USDT"],
        "intervals": {
            "klines": "1m",
            "orderbook_snapshot": "1m",
            "trades": "realtime",
            "funding": "8h",
            "mark_price": "1m",
        },
        "orderbook": {"depth": 200},
        "storage": {
            "backend": "filesystem",
            "path": "data/test",
            "compression": "gzip",
        },
        "logging": {
            "level": "INFO",
            "file": "logs/test.log",
            "format": "%(message)s",
        },
        "runtime": {
            "dry_run": False,
            "enable_metrics": True,
            "use_proxy": False,
        },
    })
    
    logger.info(f"Symbols: {', '.join(settings.symbols)}")
    logger.info(f"Intervals: {settings.intervals}")
    
    # Create mock exchange
    exchange = create_mock_exchange()
    
    # Create subscription manager
    manager = SubscriptionManager(exchange, settings)
    
    # Start subscriptions
    logger.info("Starting subscriptions...")
    await manager.start()
    
    logger.info(f"Started {manager.task_count} subscription tasks")
    
    # Run for 5 seconds and collect data
    logger.info("Collecting data for 5 seconds...")
    
    data_counts = {
        "ticker": 0,
        "orderbook": 0,
        "trades": 0,
        "ohlcv": 0,
        "funding": 0,
        "mark_price": 0,
    }
    
    start_time = asyncio.get_event_loop().time()
    while asyncio.get_event_loop().time() - start_time < 5.0:
        # Check each queue
        if not manager.ticker_queue.empty():
            data = await manager.ticker_queue.get()
            data_counts["ticker"] += 1
            logger.info(f"Ticker: {data['symbol']} = ${data['data']['last']}")
            manager.ticker_queue.task_done()
        
        if not manager.orderbook_queue.empty():
            data = await manager.orderbook_queue.get()
            data_counts["orderbook"] += 1
            bids = len(data['data']['bids'])
            asks = len(data['data']['asks'])
            logger.info(f"Orderbook: {data['symbol']} - {bids} bids, {asks} asks")
            manager.orderbook_queue.task_done()
        
        if not manager.trades_queue.empty():
            data = await manager.trades_queue.get()
            data_counts["trades"] += 1
            trade = data['data']
            logger.info(
                f"Trade: {data['symbol']} - {trade['side']} "
                f"{trade['amount']} @ ${trade['price']}"
            )
            manager.trades_queue.task_done()
        
        if not manager.ohlcv_queue.empty():
            data = await manager.ohlcv_queue.get()
            data_counts["ohlcv"] += 1
            ohlcv = data['data']
            logger.info(
                f"OHLCV: {data['symbol']} @ {data['timeframe']} - "
                f"C: ${ohlcv[4]}, V: {ohlcv[5]}"
            )
            manager.ohlcv_queue.task_done()
        
        if not manager.funding_queue.empty():
            data = await manager.funding_queue.get()
            data_counts["funding"] += 1
            logger.info(
                f"Funding: {data['symbol']} - "
                f"rate: {data['data']['fundingRate']}"
            )
            manager.funding_queue.task_done()
        
        if not manager.mark_price_queue.empty():
            data = await manager.mark_price_queue.get()
            data_counts["mark_price"] += 1
            logger.info(
                f"Mark Price: {data['symbol']} - "
                f"${data['data']['mark_price']}"
            )
            manager.mark_price_queue.task_done()
        
        await asyncio.sleep(0.1)
    
    # Stop subscriptions
    logger.info("Stopping subscriptions...")
    await manager.stop()
    
    # Summary
    logger.info("=" * 60)
    logger.info("Data Collection Summary:")
    for data_type, count in data_counts.items():
        logger.info(f"  {data_type}: {count} updates")
    logger.info("=" * 60)
    
    logger.info("Demo complete!")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Demo interrupted by user")
    except Exception as e:
        logger.exception(f"Error in demo: {e}")
        sys.exit(1)
