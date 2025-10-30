"""
Data subscription modules for continuous market data collection.

Provides async subscription tasks for:
- Ticker updates
- Order book snapshots
- Trade streams
- OHLCV/candlestick data (multiple timeframes)
- Funding rate updates
- Mark price updates

Each subscription runs as an independent async task per symbol, using ccxt.pro
watch APIs with throttling, reconnection logic, and data normalization.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional, Set

from .config import MarketDataSettings
from .exchange import ExchangeAdapter

logger = logging.getLogger(__name__)


class SubscriptionManager:
    """
    Manages lifecycle of all data subscriptions across symbols and types.
    
    Coordinates async tasks for ticker, orderbook, trades, OHLCV, funding rate,
    and mark price subscriptions. Handles throttling intervals from config and
    provides queues for downstream storage pipeline.
    """

    def __init__(
        self,
        exchange: ExchangeAdapter,
        settings: MarketDataSettings,
    ):
        """
        Initialize subscription manager.
        
        Args:
            exchange: Exchange adapter with ccxt.pro watch methods
            settings: Configuration settings
        """
        self.exchange = exchange
        self.settings = settings
        
        # Data queues for storage pipeline (one per data type)
        self.ticker_queue: asyncio.Queue = asyncio.Queue(maxsize=1000)
        self.orderbook_queue: asyncio.Queue = asyncio.Queue(maxsize=1000)
        self.trades_queue: asyncio.Queue = asyncio.Queue(maxsize=1000)
        self.ohlcv_queue: asyncio.Queue = asyncio.Queue(maxsize=1000)
        self.funding_queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        self.mark_price_queue: asyncio.Queue = asyncio.Queue(maxsize=1000)
        
        # Track active subscription tasks
        self._tasks: Set[asyncio.Task] = set()
        self._running = False
        self._stop_event = asyncio.Event()
        
        # Parse timeframes for OHLCV
        self._ohlcv_timeframes = self._parse_ohlcv_timeframes()
        
        logger.info("Subscription manager initialized")
    
    def _parse_ohlcv_timeframes(self) -> List[str]:
        """
        Parse OHLCV timeframes from config intervals.
        
        Returns:
            List of timeframes (e.g., ["1m", "5m", "1h"])
        """
        timeframes = []
        klines_interval = self.settings.intervals.get("klines", "1m")
        
        # If klines interval is a comma-separated list, split it
        if isinstance(klines_interval, str):
            timeframes = [tf.strip() for tf in klines_interval.split(",")]
        
        # Default to 1m if empty
        if not timeframes:
            timeframes = ["1m"]
        
        logger.info(f"OHLCV timeframes: {timeframes}")
        return timeframes
    
    def _parse_interval(self, interval_str: str) -> Optional[float]:
        """
        Parse interval string to seconds.
        
        Args:
            interval_str: Interval string (e.g., "1m", "5s", "1h", "realtime")
            
        Returns:
            Interval in seconds, or None for realtime
        """
        if interval_str == "realtime" or not interval_str:
            return None
        
        # Parse format like "1m", "5s", "1h", "8h"
        if interval_str[-1] == "s":
            return float(interval_str[:-1])
        elif interval_str[-1] == "m":
            return float(interval_str[:-1]) * 60
        elif interval_str[-1] == "h":
            return float(interval_str[:-1]) * 3600
        else:
            # Try to parse as raw seconds
            try:
                return float(interval_str)
            except ValueError:
                logger.warning(f"Could not parse interval '{interval_str}', using realtime")
                return None
    
    async def start(self) -> None:
        """Start all subscriptions for configured symbols."""
        if self._running:
            logger.warning("Subscription manager already running")
            return
        
        self._running = True
        self._stop_event.clear()
        
        logger.info(
            f"Starting subscriptions for {len(self.settings.symbols)} symbols: "
            f"{', '.join(self.settings.symbols)}"
        )
        
        # Start subscriptions for each symbol
        for symbol in self.settings.symbols:
            # Ticker subscription
            if "ticker" in self.settings.intervals or "klines" in self.settings.intervals:
                task = asyncio.create_task(
                    self._subscribe_ticker(symbol),
                    name=f"ticker_{symbol}"
                )
                self._tasks.add(task)
            
            # Order book subscription
            if "orderbook_snapshot" in self.settings.intervals:
                task = asyncio.create_task(
                    self._subscribe_orderbook(symbol),
                    name=f"orderbook_{symbol}"
                )
                self._tasks.add(task)
            
            # Trades subscription
            if "trades" in self.settings.intervals:
                task = asyncio.create_task(
                    self._subscribe_trades(symbol),
                    name=f"trades_{symbol}"
                )
                self._tasks.add(task)
            
            # OHLCV subscriptions (multiple timeframes)
            for timeframe in self._ohlcv_timeframes:
                task = asyncio.create_task(
                    self._subscribe_ohlcv(symbol, timeframe),
                    name=f"ohlcv_{symbol}_{timeframe}"
                )
                self._tasks.add(task)
            
            # Funding rate subscription
            if "funding" in self.settings.intervals:
                task = asyncio.create_task(
                    self._subscribe_funding(symbol),
                    name=f"funding_{symbol}"
                )
                self._tasks.add(task)
            
            # Mark price subscription
            if "mark_price" in self.settings.intervals or "funding" in self.settings.intervals:
                task = asyncio.create_task(
                    self._subscribe_mark_price(symbol),
                    name=f"mark_price_{symbol}"
                )
                self._tasks.add(task)
        
        logger.info(f"Started {len(self._tasks)} subscription tasks")
    
    async def stop(self) -> None:
        """Stop all subscriptions and clean up tasks."""
        if not self._running:
            logger.warning("Subscription manager not running")
            return
        
        logger.info("Stopping subscription manager...")
        self._running = False
        self._stop_event.set()
        
        # Cancel all tasks
        for task in self._tasks:
            if not task.done():
                task.cancel()
        
        # Wait for all tasks to complete
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        
        self._tasks.clear()
        logger.info("Subscription manager stopped")
    
    async def _subscribe_ticker(self, symbol: str) -> None:
        """
        Subscribe to ticker updates for a symbol.
        
        Args:
            symbol: Trading pair symbol (e.g., "BTC/USDT:USDT")
        """
        interval_str = self.settings.intervals.get("klines", "1m")
        interval = self._parse_interval(interval_str)
        
        logger.info(
            f"Starting ticker subscription: {symbol} "
            f"(interval: {interval_str})"
        )
        
        try:
            while self._running and not self._stop_event.is_set():
                try:
                    # Watch ticker via ccxt.pro
                    ticker = await self.exchange.watch_ticker(symbol)
                    
                    # Enqueue normalized data
                    if ticker:
                        await self.ticker_queue.put({
                            "type": "ticker",
                            "symbol": symbol,
                            "data": ticker,
                        })
                        logger.debug(f"Ticker update: {symbol} - ${ticker.get('last')}")
                    
                    # Throttle if interval specified
                    if interval:
                        await asyncio.sleep(interval)
                
                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    logger.error(f"Error in ticker subscription for {symbol}: {e}")
                    # Backoff before retry
                    await asyncio.sleep(5)
        
        except asyncio.CancelledError:
            logger.info(f"Ticker subscription cancelled: {symbol}")
        except Exception as e:
            logger.exception(f"Fatal error in ticker subscription for {symbol}: {e}")
    
    async def _subscribe_orderbook(self, symbol: str) -> None:
        """
        Subscribe to order book updates for a symbol.
        
        Args:
            symbol: Trading pair symbol
        """
        interval_str = self.settings.intervals.get("orderbook_snapshot", "1m")
        interval = self._parse_interval(interval_str)
        depth = self.settings.orderbook.depth
        
        logger.info(
            f"Starting orderbook subscription: {symbol} "
            f"(depth: {depth}, interval: {interval_str})"
        )
        
        try:
            while self._running and not self._stop_event.is_set():
                try:
                    # Watch order book via ccxt.pro
                    orderbook = await self.exchange.watch_order_book(symbol, depth)
                    
                    # Enqueue normalized data
                    if orderbook:
                        await self.orderbook_queue.put({
                            "type": "orderbook",
                            "symbol": symbol,
                            "data": orderbook,
                        })
                        logger.debug(
                            f"Orderbook update: {symbol} - "
                            f"bids: {len(orderbook.get('bids', []))}, "
                            f"asks: {len(orderbook.get('asks', []))}"
                        )
                    
                    # Throttle if interval specified
                    if interval:
                        await asyncio.sleep(interval)
                
                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    logger.error(f"Error in orderbook subscription for {symbol}: {e}")
                    await asyncio.sleep(5)
        
        except asyncio.CancelledError:
            logger.info(f"Orderbook subscription cancelled: {symbol}")
        except Exception as e:
            logger.exception(f"Fatal error in orderbook subscription for {symbol}: {e}")
    
    async def _subscribe_trades(self, symbol: str) -> None:
        """
        Subscribe to trade stream for a symbol.
        
        Args:
            symbol: Trading pair symbol
        """
        interval_str = self.settings.intervals.get("trades", "realtime")
        interval = self._parse_interval(interval_str)
        
        logger.info(
            f"Starting trades subscription: {symbol} "
            f"(interval: {interval_str})"
        )
        
        try:
            while self._running and not self._stop_event.is_set():
                try:
                    # Watch trades via ccxt.pro
                    trades = await self.exchange.watch_trades(symbol)
                    
                    # Enqueue normalized data
                    if trades:
                        for trade in trades:
                            await self.trades_queue.put({
                                "type": "trade",
                                "symbol": symbol,
                                "data": trade,
                            })
                        logger.debug(f"Trades update: {symbol} - {len(trades)} trades")
                    
                    # Throttle if interval specified
                    if interval:
                        await asyncio.sleep(interval)
                
                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    logger.error(f"Error in trades subscription for {symbol}: {e}")
                    await asyncio.sleep(5)
        
        except asyncio.CancelledError:
            logger.info(f"Trades subscription cancelled: {symbol}")
        except Exception as e:
            logger.exception(f"Fatal error in trades subscription for {symbol}: {e}")
    
    async def _subscribe_ohlcv(self, symbol: str, timeframe: str) -> None:
        """
        Subscribe to OHLCV (candlestick) updates for a symbol and timeframe.
        
        Args:
            symbol: Trading pair symbol
            timeframe: Timeframe (e.g., "1m", "5m", "1h")
        """
        interval_str = self.settings.intervals.get("klines", "1m")
        interval = self._parse_interval(interval_str)
        
        logger.info(
            f"Starting OHLCV subscription: {symbol} @ {timeframe} "
            f"(interval: {interval_str})"
        )
        
        try:
            while self._running and not self._stop_event.is_set():
                try:
                    # Watch OHLCV via ccxt.pro
                    ohlcv_list = await self.exchange.watch_ohlcv(symbol, timeframe)
                    
                    # Enqueue normalized data
                    if ohlcv_list:
                        for ohlcv in ohlcv_list:
                            await self.ohlcv_queue.put({
                                "type": "ohlcv",
                                "symbol": symbol,
                                "timeframe": timeframe,
                                "data": ohlcv,
                            })
                        logger.debug(
                            f"OHLCV update: {symbol} @ {timeframe} - "
                            f"{len(ohlcv_list)} candles"
                        )
                    
                    # Throttle if interval specified
                    if interval:
                        await asyncio.sleep(interval)
                
                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    logger.error(
                        f"Error in OHLCV subscription for {symbol} @ {timeframe}: {e}"
                    )
                    await asyncio.sleep(5)
        
        except asyncio.CancelledError:
            logger.info(f"OHLCV subscription cancelled: {symbol} @ {timeframe}")
        except Exception as e:
            logger.exception(
                f"Fatal error in OHLCV subscription for {symbol} @ {timeframe}: {e}"
            )
    
    async def _subscribe_funding(self, symbol: str) -> None:
        """
        Subscribe to funding rate updates for a symbol.
        
        Args:
            symbol: Trading pair symbol
        """
        interval_str = self.settings.intervals.get("funding", "8h")
        interval = self._parse_interval(interval_str)
        
        # Default to 8 hours for funding rate if not specified
        if interval is None:
            interval = 8 * 3600  # 8 hours in seconds
        
        logger.info(
            f"Starting funding rate subscription: {symbol} "
            f"(interval: {interval_str})"
        )
        
        try:
            while self._running and not self._stop_event.is_set():
                try:
                    # Fetch funding rate (REST API, not WebSocket)
                    funding_rate = await self.exchange.fetch_funding_rate(symbol)
                    
                    # Enqueue normalized data
                    if funding_rate:
                        await self.funding_queue.put({
                            "type": "funding_rate",
                            "symbol": symbol,
                            "data": funding_rate,
                        })
                        logger.debug(
                            f"Funding rate update: {symbol} - "
                            f"{funding_rate.get('fundingRate', 'N/A')}"
                        )
                    
                    # Wait for next interval
                    await asyncio.sleep(interval)
                
                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    logger.error(f"Error in funding rate subscription for {symbol}: {e}")
                    await asyncio.sleep(60)  # Retry after 1 minute
        
        except asyncio.CancelledError:
            logger.info(f"Funding rate subscription cancelled: {symbol}")
        except Exception as e:
            logger.exception(
                f"Fatal error in funding rate subscription for {symbol}: {e}"
            )
    
    async def _subscribe_mark_price(self, symbol: str) -> None:
        """
        Subscribe to mark price updates for a symbol.
        
        Args:
            symbol: Trading pair symbol
        """
        interval_str = self.settings.intervals.get("mark_price", "1m")
        interval = self._parse_interval(interval_str)
        
        # Default to 1 minute if not specified
        if interval is None:
            interval = 60
        
        logger.info(
            f"Starting mark price subscription: {symbol} "
            f"(interval: {interval_str})"
        )
        
        try:
            while self._running and not self._stop_event.is_set():
                try:
                    # Derive mark price from ticker
                    mark_price = await self.exchange.derive_mark_price(symbol)
                    
                    # Enqueue normalized data
                    if mark_price:
                        await self.mark_price_queue.put({
                            "type": "mark_price",
                            "symbol": symbol,
                            "data": {
                                "symbol": symbol,
                                "mark_price": mark_price,
                                "timestamp": None,  # Will be set by storage layer
                            },
                        })
                        logger.debug(f"Mark price update: {symbol} - ${mark_price}")
                    
                    # Wait for next interval
                    await asyncio.sleep(interval)
                
                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    logger.error(f"Error in mark price subscription for {symbol}: {e}")
                    await asyncio.sleep(30)  # Retry after 30 seconds
        
        except asyncio.CancelledError:
            logger.info(f"Mark price subscription cancelled: {symbol}")
        except Exception as e:
            logger.exception(
                f"Fatal error in mark price subscription for {symbol}: {e}"
            )
    
    def get_queue_sizes(self) -> Dict[str, int]:
        """
        Get current queue sizes for monitoring.
        
        Returns:
            Dictionary mapping queue names to their sizes
        """
        return {
            "ticker": self.ticker_queue.qsize(),
            "orderbook": self.orderbook_queue.qsize(),
            "trades": self.trades_queue.qsize(),
            "ohlcv": self.ohlcv_queue.qsize(),
            "funding": self.funding_queue.qsize(),
            "mark_price": self.mark_price_queue.qsize(),
        }
    
    @property
    def is_running(self) -> bool:
        """Check if subscription manager is running."""
        return self._running
    
    @property
    def task_count(self) -> int:
        """Get count of active subscription tasks."""
        return len(self._tasks)


__all__ = ["SubscriptionManager"]
