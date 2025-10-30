"""
Integration tests for subscription system.

Tests subscription manager with mock exchange data.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from market_data_collector import SubscriptionManager
from market_data_collector.config import MarketDataSettings
from market_data_collector.exchange import ExchangeAdapter


@pytest.fixture
def mock_settings():
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


@pytest.fixture
def mock_exchange():
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


@pytest.mark.asyncio
async def test_subscription_manager_init(mock_exchange, mock_settings):
    """Test subscription manager initialization."""
    manager = SubscriptionManager(mock_exchange, mock_settings)
    
    assert manager.exchange == mock_exchange
    assert manager.settings == mock_settings
    assert not manager.is_running
    assert manager.task_count == 0
    assert manager.ticker_queue.qsize() == 0


@pytest.mark.asyncio
async def test_subscription_manager_start_stop(mock_exchange, mock_settings):
    """Test starting and stopping subscription manager."""
    manager = SubscriptionManager(mock_exchange, mock_settings)
    
    # Start subscriptions
    await manager.start()
    assert manager.is_running
    assert manager.task_count > 0  # Should have created tasks
    
    # Give tasks time to start
    await asyncio.sleep(0.1)
    
    # Stop subscriptions
    await manager.stop()
    assert not manager.is_running
    assert manager.task_count == 0


@pytest.mark.asyncio
async def test_parse_interval(mock_exchange, mock_settings):
    """Test interval parsing."""
    manager = SubscriptionManager(mock_exchange, mock_settings)
    
    assert manager._parse_interval("realtime") is None
    assert manager._parse_interval("30s") == 30.0
    assert manager._parse_interval("5m") == 300.0
    assert manager._parse_interval("1h") == 3600.0
    assert manager._parse_interval("8h") == 28800.0


@pytest.mark.asyncio
async def test_parse_ohlcv_timeframes(mock_exchange, mock_settings):
    """Test OHLCV timeframe parsing."""
    manager = SubscriptionManager(mock_exchange, mock_settings)
    
    timeframes = manager._parse_ohlcv_timeframes()
    assert "1m" in timeframes
    assert "5m" in timeframes
    assert len(timeframes) == 2


@pytest.mark.asyncio
async def test_ticker_subscription(mock_exchange, mock_settings):
    """Test ticker subscription receives data."""
    manager = SubscriptionManager(mock_exchange, mock_settings)
    
    await manager.start()
    
    # Wait for some data
    await asyncio.sleep(0.5)
    
    # Check if data was queued
    assert manager.ticker_queue.qsize() > 0
    
    # Get data
    data = await manager.ticker_queue.get()
    assert data["type"] == "ticker"
    assert data["symbol"] in mock_settings.symbols
    assert "last" in data["data"]
    
    await manager.stop()


@pytest.mark.asyncio
async def test_orderbook_subscription(mock_exchange, mock_settings):
    """Test orderbook subscription receives data."""
    manager = SubscriptionManager(mock_exchange, mock_settings)
    
    await manager.start()
    
    # Wait for some data
    await asyncio.sleep(0.5)
    
    # Check if data was queued
    assert manager.orderbook_queue.qsize() > 0
    
    # Get data
    data = await manager.orderbook_queue.get()
    assert data["type"] == "orderbook"
    assert "bids" in data["data"]
    assert "asks" in data["data"]
    
    await manager.stop()


@pytest.mark.asyncio
async def test_trades_subscription(mock_exchange, mock_settings):
    """Test trades subscription receives data."""
    manager = SubscriptionManager(mock_exchange, mock_settings)
    
    await manager.start()
    
    # Wait for some data
    await asyncio.sleep(0.5)
    
    # Check if data was queued
    assert manager.trades_queue.qsize() > 0
    
    # Get data
    data = await manager.trades_queue.get()
    assert data["type"] == "trade"
    assert "price" in data["data"]
    assert "amount" in data["data"]
    
    await manager.stop()


@pytest.mark.asyncio
async def test_ohlcv_subscription(mock_exchange, mock_settings):
    """Test OHLCV subscription receives data."""
    manager = SubscriptionManager(mock_exchange, mock_settings)
    
    await manager.start()
    
    # Wait for some data
    await asyncio.sleep(0.5)
    
    # Check if data was queued
    assert manager.ohlcv_queue.qsize() > 0
    
    # Get data
    data = await manager.ohlcv_queue.get()
    assert data["type"] == "ohlcv"
    assert data["timeframe"] in ["1m", "5m"]
    assert len(data["data"]) == 6  # [timestamp, O, H, L, C, V]
    
    await manager.stop()


@pytest.mark.asyncio
async def test_funding_subscription(mock_exchange, mock_settings):
    """Test funding rate subscription receives data."""
    manager = SubscriptionManager(mock_exchange, mock_settings)
    
    await manager.start()
    
    # Wait for some data
    await asyncio.sleep(0.5)
    
    # Check if data was queued
    assert manager.funding_queue.qsize() > 0
    
    # Get data
    data = await manager.funding_queue.get()
    assert data["type"] == "funding_rate"
    assert "fundingRate" in data["data"]
    
    await manager.stop()


@pytest.mark.asyncio
async def test_mark_price_subscription(mock_exchange, mock_settings):
    """Test mark price subscription receives data."""
    manager = SubscriptionManager(mock_exchange, mock_settings)
    
    await manager.start()
    
    # Wait for some data
    await asyncio.sleep(0.5)
    
    # Check if data was queued
    assert manager.mark_price_queue.qsize() > 0
    
    # Get data
    data = await manager.mark_queue.get()
    assert data["type"] == "mark_price"
    assert "mark_price" in data["data"]
    
    await manager.stop()


@pytest.mark.asyncio
async def test_get_queue_sizes(mock_exchange, mock_settings):
    """Test getting queue sizes."""
    manager = SubscriptionManager(mock_exchange, mock_settings)
    
    sizes = manager.get_queue_sizes()
    assert "ticker" in sizes
    assert "orderbook" in sizes
    assert "trades" in sizes
    assert "ohlcv" in sizes
    assert "funding" in sizes
    assert "mark_price" in sizes
    assert all(size >= 0 for size in sizes.values())


@pytest.mark.asyncio
async def test_multiple_symbols(mock_exchange, mock_settings):
    """Test subscriptions for multiple symbols."""
    manager = SubscriptionManager(mock_exchange, mock_settings)
    
    await manager.start()
    
    # Should have tasks for both BTC and ETH
    assert manager.task_count >= 2 * 6  # 2 symbols × 6 data types (min)
    
    await manager.stop()


@pytest.mark.asyncio
async def test_error_recovery(mock_exchange, mock_settings):
    """Test error recovery in subscriptions."""
    # Make watch_ticker fail first time, then succeed
    call_count = 0
    
    async def failing_ticker(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise Exception("Simulated error")
        return {
            "symbol": "BTC/USDT:USDT",
            "timestamp": 1698765432000,
            "last": 35000.0,
        }
    
    mock_exchange.watch_ticker = AsyncMock(side_effect=failing_ticker)
    
    manager = SubscriptionManager(mock_exchange, mock_settings)
    await manager.start()
    
    # Wait for retry
    await asyncio.sleep(6)  # Backoff is 5 seconds
    
    # Should have recovered
    assert manager.ticker_queue.qsize() > 0
    
    await manager.stop()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
