"""
Simple integration tests for subscription system.

Tests subscription manager with mock exchange data.
Run with: python test_subscriptions_simple.py
"""

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from market_data_collector import SubscriptionManager
from market_data_collector.config import MarketDataSettings
from market_data_collector.exchange import ExchangeAdapter


def create_mock_settings():
    """Create mock settings for testing."""
    return MarketDataSettings.model_validate({
        "exchange": {
            "name": "Bybit",
            "market_type": "usdt_perpetual",
            "base_rest_url": "https://api.bybit.com",
            "base_websocket_url": "wss://stream.bybit.com/v5/public/linear",
        },
        "symbols": ["BTC/USDT:USDT", "ETH/USDT:USDT"],
        "intervals": {
            "klines": "1m,5m",
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


def create_mock_exchange():
    """Create mock exchange adapter."""
    exchange = MagicMock(spec=ExchangeAdapter)
    
    # Mock watch methods
    exchange.watch_ticker = AsyncMock(return_value={
        "symbol": "BTC/USDT:USDT",
        "timestamp": 1698765432000,
        "last": 35000.0,
        "bid": 34999.5,
        "ask": 35000.5,
    })
    
    exchange.watch_order_book = AsyncMock(return_value={
        "symbol": "BTC/USDT:USDT",
        "timestamp": 1698765432000,
        "bids": [[34999.5, 1.5], [34999.0, 2.3]],
        "asks": [[35000.5, 1.8], [35001.0, 2.1]],
    })
    
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
    
    exchange.watch_ohlcv = AsyncMock(return_value=[
        [1698765420000, 34990.0, 35010.0, 34980.0, 35000.0, 123.45]
    ])
    
    exchange.fetch_funding_rate = AsyncMock(return_value={
        "symbol": "BTC/USDT:USDT",
        "fundingRate": 0.0001,
        "fundingTimestamp": 1698768000000,
        "timestamp": 1698765432000,
    })
    
    exchange.derive_mark_price = AsyncMock(return_value=35005.5)
    
    return exchange


async def test_subscription_manager_init():
    """Test subscription manager initialization."""
    print("Testing subscription manager initialization...")
    
    mock_exchange = create_mock_exchange()
    mock_settings = create_mock_settings()
    
    manager = SubscriptionManager(mock_exchange, mock_settings)
    
    assert manager.exchange == mock_exchange
    assert manager.settings == mock_settings
    assert not manager.is_running
    assert manager.task_count == 0
    assert manager.ticker_queue.qsize() == 0
    
    print("✓ Subscription manager initialization test passed")


async def test_subscription_manager_start_stop():
    """Test starting and stopping subscription manager."""
    print("Testing subscription manager start/stop...")
    
    mock_exchange = create_mock_exchange()
    mock_settings = create_mock_settings()
    
    manager = SubscriptionManager(mock_exchange, mock_settings)
    
    # Start subscriptions
    await manager.start()
    assert manager.is_running
    assert manager.task_count > 0  # Should have created tasks
    
    print(f"  Created {manager.task_count} subscription tasks")
    
    # Give tasks time to start
    await asyncio.sleep(0.1)
    
    # Stop subscriptions
    await manager.stop()
    assert not manager.is_running
    assert manager.task_count == 0
    
    print("✓ Subscription manager start/stop test passed")


async def test_parse_interval():
    """Test interval parsing."""
    print("Testing interval parsing...")
    
    mock_exchange = create_mock_exchange()
    mock_settings = create_mock_settings()
    
    manager = SubscriptionManager(mock_exchange, mock_settings)
    
    assert manager._parse_interval("realtime") is None
    assert manager._parse_interval("30s") == 30.0
    assert manager._parse_interval("5m") == 300.0
    assert manager._parse_interval("1h") == 3600.0
    assert manager._parse_interval("8h") == 28800.0
    
    print("✓ Interval parsing test passed")


async def test_parse_ohlcv_timeframes():
    """Test OHLCV timeframe parsing."""
    print("Testing OHLCV timeframe parsing...")
    
    mock_exchange = create_mock_exchange()
    mock_settings = create_mock_settings()
    
    manager = SubscriptionManager(mock_exchange, mock_settings)
    
    timeframes = manager._parse_ohlcv_timeframes()
    assert "1m" in timeframes
    assert "5m" in timeframes
    assert len(timeframes) == 2
    
    print(f"  Parsed timeframes: {timeframes}")
    print("✓ OHLCV timeframe parsing test passed")


async def test_ticker_subscription():
    """Test ticker subscription receives data."""
    print("Testing ticker subscription...")
    
    mock_exchange = create_mock_exchange()
    mock_settings = create_mock_settings()
    
    manager = SubscriptionManager(mock_exchange, mock_settings)
    
    await manager.start()
    
    # Wait for some data
    await asyncio.sleep(0.5)
    
    # Check if data was queued
    assert manager.ticker_queue.qsize() > 0
    print(f"  Received {manager.ticker_queue.qsize()} ticker updates")
    
    # Get data
    data = await manager.ticker_queue.get()
    assert data["type"] == "ticker"
    assert data["symbol"] in mock_settings.symbols
    assert "last" in data["data"]
    
    await manager.stop()
    
    print("✓ Ticker subscription test passed")


async def test_orderbook_subscription():
    """Test orderbook subscription receives data."""
    print("Testing orderbook subscription...")
    
    mock_exchange = create_mock_exchange()
    mock_settings = create_mock_settings()
    
    manager = SubscriptionManager(mock_exchange, mock_settings)
    
    await manager.start()
    
    # Wait for some data
    await asyncio.sleep(0.5)
    
    # Check if data was queued
    assert manager.orderbook_queue.qsize() > 0
    print(f"  Received {manager.orderbook_queue.qsize()} orderbook updates")
    
    # Get data
    data = await manager.orderbook_queue.get()
    assert data["type"] == "orderbook"
    assert "bids" in data["data"]
    assert "asks" in data["data"]
    
    await manager.stop()
    
    print("✓ Orderbook subscription test passed")


async def test_trades_subscription():
    """Test trades subscription receives data."""
    print("Testing trades subscription...")
    
    mock_exchange = create_mock_exchange()
    mock_settings = create_mock_settings()
    
    manager = SubscriptionManager(mock_exchange, mock_settings)
    
    await manager.start()
    
    # Wait for some data
    await asyncio.sleep(0.5)
    
    # Check if data was queued
    assert manager.trades_queue.qsize() > 0
    print(f"  Received {manager.trades_queue.qsize()} trade updates")
    
    # Get data
    data = await manager.trades_queue.get()
    assert data["type"] == "trade"
    assert "price" in data["data"]
    assert "amount" in data["data"]
    
    await manager.stop()
    
    print("✓ Trades subscription test passed")


async def test_ohlcv_subscription():
    """Test OHLCV subscription receives data."""
    print("Testing OHLCV subscription...")
    
    mock_exchange = create_mock_exchange()
    mock_settings = create_mock_settings()
    
    manager = SubscriptionManager(mock_exchange, mock_settings)
    
    await manager.start()
    
    # Wait for some data
    await asyncio.sleep(0.5)
    
    # Check if data was queued
    assert manager.ohlcv_queue.qsize() > 0
    print(f"  Received {manager.ohlcv_queue.qsize()} OHLCV updates")
    
    # Get data
    data = await manager.ohlcv_queue.get()
    assert data["type"] == "ohlcv"
    assert data["timeframe"] in ["1m", "5m"]
    assert len(data["data"]) == 6  # [timestamp, O, H, L, C, V]
    
    await manager.stop()
    
    print("✓ OHLCV subscription test passed")


async def test_get_queue_sizes():
    """Test getting queue sizes."""
    print("Testing queue size monitoring...")
    
    mock_exchange = create_mock_exchange()
    mock_settings = create_mock_settings()
    
    manager = SubscriptionManager(mock_exchange, mock_settings)
    
    sizes = manager.get_queue_sizes()
    assert "ticker" in sizes
    assert "orderbook" in sizes
    assert "trades" in sizes
    assert "ohlcv" in sizes
    assert "funding" in sizes
    assert "mark_price" in sizes
    assert all(size >= 0 for size in sizes.values())
    
    print(f"  Queue sizes: {sizes}")
    print("✓ Queue size monitoring test passed")


async def test_multiple_symbols():
    """Test subscriptions for multiple symbols."""
    print("Testing multiple symbol subscriptions...")
    
    mock_exchange = create_mock_exchange()
    mock_settings = create_mock_settings()
    
    manager = SubscriptionManager(mock_exchange, mock_settings)
    
    await manager.start()
    
    # Should have tasks for both BTC and ETH
    # 2 symbols × (1 ticker + 1 orderbook + 1 trades + 2 OHLCV + 1 funding + 1 mark_price) = 14 tasks
    assert manager.task_count >= 12  # At least 12 tasks
    print(f"  Created {manager.task_count} tasks for {len(mock_settings.symbols)} symbols")
    
    await manager.stop()
    
    print("✓ Multiple symbol subscription test passed")


async def run_all_tests():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("Running Subscription System Tests")
    print("=" * 60 + "\n")
    
    tests = [
        test_subscription_manager_init,
        test_subscription_manager_start_stop,
        test_parse_interval,
        test_parse_ohlcv_timeframes,
        test_ticker_subscription,
        test_orderbook_subscription,
        test_trades_subscription,
        test_ohlcv_subscription,
        test_get_queue_sizes,
        test_multiple_symbols,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            await test()
            passed += 1
        except AssertionError as e:
            print(f"✗ {test.__name__} failed: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {test.__name__} errored: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 60 + "\n")
    
    return failed == 0


if __name__ == "__main__":
    try:
        success = asyncio.run(run_all_tests())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nFatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
