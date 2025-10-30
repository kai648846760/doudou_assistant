#!/usr/bin/env python3
"""
Example script demonstrating data subscriptions with ccxt.pro.

This script starts the subscription manager and continuously collects market data
for configured symbols. Data is queued and can be consumed by storage writers.
"""

import asyncio
import logging
import signal
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from market_data_collector import (
    ExchangeAdapter,
    SubscriptionManager,
    configure_logging,
    settings,
)

logger = logging.getLogger(__name__)


async def consume_queue(queue: asyncio.Queue, queue_name: str, running: asyncio.Event):
    """
    Simple consumer that prints data from a queue.
    
    In production, this would write to storage (SQLite, Parquet, etc.)
    """
    logger.info(f"Starting consumer for {queue_name} queue")
    
    try:
        while running.is_set():
            try:
                # Wait for data with timeout to check running flag
                data = await asyncio.wait_for(queue.get(), timeout=1.0)
                
                # Process data (in production, write to storage)
                data_type = data.get("type")
                symbol = data.get("symbol")
                payload = data.get("data")
                
                if data_type == "ticker":
                    logger.info(
                        f"[{queue_name}] {symbol} ticker: "
                        f"last=${payload.get('last')}, "
                        f"bid=${payload.get('bid')}, "
                        f"ask=${payload.get('ask')}"
                    )
                elif data_type == "orderbook":
                    bids = len(payload.get("bids", []))
                    asks = len(payload.get("asks", []))
                    logger.info(
                        f"[{queue_name}] {symbol} orderbook: "
                        f"{bids} bids, {asks} asks"
                    )
                elif data_type == "trade":
                    logger.info(
                        f"[{queue_name}] {symbol} trade: "
                        f"{payload.get('side')} {payload.get('amount')} @ ${payload.get('price')}"
                    )
                elif data_type == "ohlcv":
                    timeframe = data.get("timeframe")
                    ohlcv = payload
                    logger.info(
                        f"[{queue_name}] {symbol} @ {timeframe} OHLCV: "
                        f"O:{ohlcv[1]}, H:{ohlcv[2]}, L:{ohlcv[3]}, C:{ohlcv[4]}, V:{ohlcv[5]}"
                    )
                elif data_type == "funding_rate":
                    logger.info(
                        f"[{queue_name}] {symbol} funding rate: "
                        f"{payload.get('fundingRate')}"
                    )
                elif data_type == "mark_price":
                    logger.info(
                        f"[{queue_name}] {symbol} mark price: "
                        f"${payload.get('mark_price')}"
                    )
                
                # Mark task as done
                queue.task_done()
                
            except asyncio.TimeoutError:
                # No data available, continue checking
                continue
    
    except asyncio.CancelledError:
        logger.info(f"Consumer for {queue_name} cancelled")
    except Exception as e:
        logger.exception(f"Error in {queue_name} consumer: {e}")


async def main():
    """Main entry point for subscription demo."""
    configure_logging()
    
    logger.info("=" * 60)
    logger.info("Market Data Subscription Demo")
    logger.info("=" * 60)
    logger.info(f"Exchange: {settings.exchange.name}")
    logger.info(f"Market Type: {settings.exchange.market_type}")
    logger.info(f"Symbols: {', '.join(settings.symbols)}")
    logger.info(f"Intervals: {settings.intervals}")
    logger.info("=" * 60)
    
    # Create exchange adapter
    exchange = ExchangeAdapter(
        exchange_name=settings.exchange.name.lower(),
        default_type=settings.exchange.market_type,
        sandbox=False,
    )
    
    # Create subscription manager
    sub_manager = SubscriptionManager(exchange, settings)
    
    # Event to control consumer tasks
    running = asyncio.Event()
    running.set()
    
    # Start consumer tasks for each queue
    consumers = [
        asyncio.create_task(
            consume_queue(sub_manager.ticker_queue, "ticker", running),
            name="consumer_ticker"
        ),
        asyncio.create_task(
            consume_queue(sub_manager.orderbook_queue, "orderbook", running),
            name="consumer_orderbook"
        ),
        asyncio.create_task(
            consume_queue(sub_manager.trades_queue, "trades", running),
            name="consumer_trades"
        ),
        asyncio.create_task(
            consume_queue(sub_manager.ohlcv_queue, "ohlcv", running),
            name="consumer_ohlcv"
        ),
        asyncio.create_task(
            consume_queue(sub_manager.funding_queue, "funding", running),
            name="consumer_funding"
        ),
        asyncio.create_task(
            consume_queue(sub_manager.mark_price_queue, "mark_price", running),
            name="consumer_mark_price"
        ),
    ]
    
    # Setup signal handlers for graceful shutdown
    stop_event = asyncio.Event()
    
    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}, shutting down...")
        stop_event.set()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Start subscriptions
        await sub_manager.start()
        
        logger.info("Subscriptions started. Press Ctrl+C to stop.")
        
        # Monitor subscriptions
        while not stop_event.is_set():
            await asyncio.sleep(10)
            
            # Log queue sizes
            queue_sizes = sub_manager.get_queue_sizes()
            logger.info(
                f"Queue sizes: {', '.join(f'{k}={v}' for k, v in queue_sizes.items())}"
            )
            logger.info(f"Active tasks: {sub_manager.task_count}")
    
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    except Exception as e:
        logger.exception(f"Error in main loop: {e}")
    finally:
        # Stop subscriptions
        logger.info("Stopping subscriptions...")
        await sub_manager.stop()
        
        # Stop consumers
        running.clear()
        for consumer in consumers:
            if not consumer.done():
                consumer.cancel()
        
        await asyncio.gather(*consumers, return_exceptions=True)
        
        # Close exchange
        await exchange.close()
        
        logger.info("Shutdown complete")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Exiting...")
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        sys.exit(1)
