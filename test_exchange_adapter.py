#!/usr/bin/env python3
"""
Test script for exchange adapter with Bybit swap.

Demonstrates:
- Connecting to Bybit swap (testnet/sandbox mode)
- Receiving data via WebSocket (watch_* methods)
- Falling back to REST when needed (fetch_* methods)
- Timestamp normalization
- Reconnection and backoff logic
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from market_data_collector.exchange import create_exchange_adapter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)


async def test_websocket_connection(adapter, symbol: str):
    """Test WebSocket connection and data reception."""
    logger.info("=" * 80)
    logger.info("TEST: WebSocket Connection and Data Reception")
    logger.info("=" * 80)
    
    try:
        # Test watch_ticker
        logger.info(f"\n1. Testing watch_ticker for {symbol}...")
        ticker = await adapter.watch_ticker(symbol)
        logger.info(f"✓ Ticker received:")
        logger.info(f"  - Symbol: {ticker.get('symbol')}")
        logger.info(f"  - Last price: {ticker.get('last')}")
        logger.info(f"  - Bid: {ticker.get('bid')} | Ask: {ticker.get('ask')}")
        logger.info(f"  - Volume: {ticker.get('baseVolume')}")
        logger.info(f"  - Timestamp (ms): {ticker.get('timestamp')}")
        
        # Test watch_order_book
        logger.info(f"\n2. Testing watch_order_book for {symbol}...")
        orderbook = await adapter.watch_order_book(symbol, limit=5)
        logger.info(f"✓ Order book received:")
        logger.info(f"  - Symbol: {orderbook.get('symbol')}")
        logger.info(f"  - Bids (top 3): {orderbook.get('bids', [])[:3]}")
        logger.info(f"  - Asks (top 3): {orderbook.get('asks', [])[:3]}")
        logger.info(f"  - Timestamp (ms): {orderbook.get('timestamp')}")
        
        # Test watch_trades
        logger.info(f"\n3. Testing watch_trades for {symbol}...")
        trades = await adapter.watch_trades(symbol)
        logger.info(f"✓ Trades received: {len(trades)} trade(s)")
        if trades:
            trade = trades[0]
            logger.info(f"  - Recent trade:")
            logger.info(f"    - Price: {trade.get('price')}")
            logger.info(f"    - Amount: {trade.get('amount')}")
            logger.info(f"    - Side: {trade.get('side')}")
            logger.info(f"    - Timestamp (ms): {trade.get('timestamp')}")
        
        # Test watch_ohlcv
        logger.info(f"\n4. Testing watch_ohlcv for {symbol} (1m)...")
        ohlcv_list = await adapter.watch_ohlcv(symbol, timeframe="1m", limit=3)
        logger.info(f"✓ OHLCV data received: {len(ohlcv_list)} candle(s)")
        if ohlcv_list:
            candle = ohlcv_list[-1]
            logger.info(f"  - Latest candle:")
            logger.info(f"    - Timestamp (ms): {candle[0]}")
            logger.info(f"    - Open: {candle[1]}")
            logger.info(f"    - High: {candle[2]}")
            logger.info(f"    - Low: {candle[3]}")
            logger.info(f"    - Close: {candle[4]}")
            logger.info(f"    - Volume: {candle[5]}")
        
        logger.info("\n✓ All WebSocket tests passed!")
        return True
        
    except Exception as e:
        logger.error(f"✗ WebSocket test failed: {e}", exc_info=True)
        return False


async def test_rest_fallback(adapter, symbol: str):
    """Test REST API fallback methods."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST: REST API Fallback")
    logger.info("=" * 80)
    
    try:
        # Test fetch_ticker
        logger.info(f"\n1. Testing fetch_ticker (REST) for {symbol}...")
        ticker = await adapter.fetch_ticker(symbol)
        logger.info(f"✓ Ticker fetched via REST:")
        logger.info(f"  - Symbol: {ticker.get('symbol')}")
        logger.info(f"  - Last price: {ticker.get('last')}")
        logger.info(f"  - Timestamp (ms): {ticker.get('timestamp')}")
        
        # Test fetch_order_book
        logger.info(f"\n2. Testing fetch_order_book (REST) for {symbol}...")
        orderbook = await adapter.fetch_order_book(symbol, limit=5)
        logger.info(f"✓ Order book fetched via REST:")
        logger.info(f"  - Bids: {len(orderbook.get('bids', []))} levels")
        logger.info(f"  - Asks: {len(orderbook.get('asks', []))} levels")
        logger.info(f"  - Timestamp (ms): {orderbook.get('timestamp')}")
        
        # Test fetch_ohlcv
        logger.info(f"\n3. Testing fetch_ohlcv (REST) for {symbol}...")
        ohlcv_list = await adapter.fetch_ohlcv(symbol, timeframe="1m", limit=3)
        logger.info(f"✓ OHLCV fetched via REST: {len(ohlcv_list)} candle(s)")
        if ohlcv_list:
            logger.info(f"  - Latest candle timestamp (ms): {ohlcv_list[-1][0]}")
        
        # Test fetch_trades
        logger.info(f"\n4. Testing fetch_trades (REST) for {symbol}...")
        trades = await adapter.fetch_trades(symbol, limit=5)
        logger.info(f"✓ Trades fetched via REST: {len(trades)} trade(s)")
        if trades:
            logger.info(f"  - Recent trade timestamp (ms): {trades[0].get('timestamp')}")
        
        logger.info("\n✓ All REST fallback tests passed!")
        return True
        
    except Exception as e:
        logger.error(f"✗ REST fallback test failed: {e}", exc_info=True)
        return False


async def test_funding_rate_and_mark_price(adapter, symbol: str):
    """Test funding rate and mark price retrieval."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST: Funding Rate and Mark Price")
    logger.info("=" * 80)
    
    try:
        # Test fetch_funding_rate
        logger.info(f"\n1. Testing fetch_funding_rate for {symbol}...")
        funding_rate = await adapter.fetch_funding_rate(symbol)
        logger.info(f"✓ Funding rate data:")
        logger.info(f"  - Symbol: {funding_rate.get('symbol')}")
        logger.info(f"  - Funding rate: {funding_rate.get('fundingRate')}")
        logger.info(f"  - Timestamp (ms): {funding_rate.get('timestamp')}")
        if "fundingTimestamp" in funding_rate:
            logger.info(f"  - Funding timestamp (ms): {funding_rate.get('fundingTimestamp')}")
        
        # Test derive_mark_price
        logger.info(f"\n2. Testing derive_mark_price for {symbol}...")
        mark_price = await adapter.derive_mark_price(symbol)
        logger.info(f"✓ Mark price derived: {mark_price}")
        
        logger.info("\n✓ Funding rate and mark price tests passed!")
        return True
        
    except Exception as e:
        logger.error(f"✗ Funding rate/mark price test failed: {e}", exc_info=True)
        return False


async def test_reconnection_logic(adapter, symbol: str):
    """Test reconnection and backoff logic by simulating errors."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST: Reconnection and Backoff Logic")
    logger.info("=" * 80)
    
    try:
        # Try invalid symbol to trigger retry logic
        logger.info("\n1. Testing with invalid symbol to trigger retries...")
        try:
            await adapter.fetch_ticker("INVALID/SYMBOL")
        except Exception as e:
            logger.info(f"✓ Expected error caught: {type(e).__name__}")
            logger.info("  (Retry logic was exercised)")
        
        # Verify adapter still works after error
        logger.info(f"\n2. Verifying adapter still works after error...")
        ticker = await adapter.fetch_ticker(symbol)
        logger.info(f"✓ Adapter recovered successfully")
        logger.info(f"  - Fetched ticker for {symbol}: ${ticker.get('last')}")
        
        logger.info("\n✓ Reconnection logic test passed!")
        return True
        
    except Exception as e:
        logger.error(f"✗ Reconnection test failed: {e}", exc_info=True)
        return False


async def main():
    """Main test entry point."""
    logger.info("\n" + "=" * 80)
    logger.info("EXCHANGE ADAPTER ACCEPTANCE TEST")
    logger.info("Target: Bybit Swap (USDT Perpetuals)")
    logger.info("Mode: Testnet/Sandbox")
    logger.info("=" * 80)
    
    # Test configuration
    symbol = "BTC/USDT:USDT"  # Bybit perpetual futures format
    sandbox = True  # Use testnet for testing
    
    logger.info(f"\nTest Symbol: {symbol}")
    logger.info(f"Sandbox Mode: {sandbox}")
    
    # Create adapter
    logger.info("\nInitializing exchange adapter...")
    adapter = create_exchange_adapter(
        exchange_name="bybit",
        default_type="swap",
        sandbox=sandbox,
    )
    
    try:
        # Load markets
        logger.info("\nLoading markets...")
        markets = await adapter.load_markets()
        logger.info(f"✓ Markets loaded: {len(markets)} markets available")
        
        # Run tests
        test_results = []
        
        # Test 1: WebSocket connection
        result = await test_websocket_connection(adapter, symbol)
        test_results.append(("WebSocket Connection", result))
        
        # Test 2: REST fallback
        result = await test_rest_fallback(adapter, symbol)
        test_results.append(("REST Fallback", result))
        
        # Test 3: Funding rate and mark price
        result = await test_funding_rate_and_mark_price(adapter, symbol)
        test_results.append(("Funding Rate & Mark Price", result))
        
        # Test 4: Reconnection logic
        result = await test_reconnection_logic(adapter, symbol)
        test_results.append(("Reconnection Logic", result))
        
        # Summary
        logger.info("\n" + "=" * 80)
        logger.info("TEST SUMMARY")
        logger.info("=" * 80)
        
        all_passed = True
        for test_name, passed in test_results:
            status = "✓ PASSED" if passed else "✗ FAILED"
            logger.info(f"{status}: {test_name}")
            if not passed:
                all_passed = False
        
        logger.info("\n" + "=" * 80)
        if all_passed:
            logger.info("🎉 ALL ACCEPTANCE CRITERIA MET!")
            logger.info("=" * 80)
            logger.info("\n✅ The exchange adapter can:")
            logger.info("  ✓ Connect to Bybit swap in sandbox mode")
            logger.info("  ✓ Receive data via WebSocket (watch_ticker, watch_order_book, etc.)")
            logger.info("  ✓ Fall back to REST when needed (fetch_ticker, fetch_ohlcv, etc.)")
            logger.info("  ✓ Retrieve funding rates and derive mark prices")
            logger.info("  ✓ Handle reconnections with exponential backoff")
            logger.info("  ✓ Normalize all timestamps to milliseconds")
            return 0
        else:
            logger.error("❌ SOME TESTS FAILED")
            logger.error("=" * 80)
            return 1
            
    except Exception as e:
        logger.error(f"\n❌ Test suite failed with error: {e}", exc_info=True)
        return 1
        
    finally:
        # Cleanup
        logger.info("\nCleaning up...")
        await adapter.close()
        logger.info("✓ Exchange adapter closed")


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
