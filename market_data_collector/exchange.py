"""
Exchange adapter for ccxt.pro with WebSocket watchers and REST fallback.

Provides async wrappers for Bybit swap market data collection with:
- WebSocket watchers (ticker, order book, trades, OHLCV)
- REST fallback methods
- Reconnection and backoff logic
- Configurable sandbox mode
- Timestamp normalization to milliseconds
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional

import ccxt
import ccxt.pro as ccxtpro

logger = logging.getLogger(__name__)


class ExchangeAdapter:
    """
    Exchange adapter using ccxt.pro for WebSocket and ccxt for REST fallback.
    
    Initializes both async (WebSocket) and sync (REST) exchange instances.
    Provides unified interface for market data collection with automatic
    reconnection and backoff logic.
    """

    def __init__(
        self,
        exchange_name: str = "bybit",
        default_type: str = "swap",
        sandbox: bool = False,
        api_key: Optional[str] = None,
        secret: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize exchange adapter with ccxt.pro and ccxt instances.
        
        Args:
            exchange_name: Name of the exchange (e.g., "bybit")
            default_type: Market type (default: "swap" for perpetual futures)
            sandbox: Enable sandbox/testnet mode
            api_key: API key for authenticated endpoints (optional)
            secret: API secret for authenticated endpoints (optional)
            options: Additional exchange-specific options
        """
        self.exchange_name = exchange_name
        self.default_type = default_type
        self.sandbox = sandbox
        
        # Configuration for both instances
        config = {
            "enableRateLimit": True,
            "options": {"defaultType": default_type},
        }
        
        if api_key and secret:
            config["apiKey"] = api_key
            config["secret"] = secret
        
        if options:
            config["options"].update(options)
        
        # Initialize async exchange (ccxt.pro) for WebSocket
        exchange_class_pro = getattr(ccxtpro, exchange_name)
        self.exchange_pro: ccxtpro.Exchange = exchange_class_pro(config)
        
        # Initialize sync exchange (ccxt) for REST fallback
        exchange_class = getattr(ccxt, exchange_name)
        self.exchange: ccxt.Exchange = exchange_class(config)
        
        # Enable sandbox mode if requested
        if sandbox:
            self.exchange_pro.set_sandbox_mode(True)
            self.exchange.set_sandbox_mode(True)
            logger.info(f"Sandbox mode enabled for {exchange_name}")
        
        # Reconnection settings
        self.max_retries = 5
        self.base_backoff = 1.0  # seconds
        self.max_backoff = 60.0  # seconds
        
        # Track connection state
        self._connected = False
        self._watch_tasks: Dict[str, asyncio.Task] = {}
        
        logger.info(
            f"Exchange adapter initialized: {exchange_name} "
            f"(type={default_type}, sandbox={sandbox})"
        )
    
    async def close(self) -> None:
        """Close exchange connections and clean up resources."""
        # Cancel all watch tasks
        for task_name, task in list(self._watch_tasks.items()):
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                logger.debug(f"Cancelled watch task: {task_name}")
        
        self._watch_tasks.clear()
        
        # Close async exchange
        if hasattr(self.exchange_pro, "close"):
            await self.exchange_pro.close()
        
        # Close sync exchange
        if hasattr(self.exchange, "close"):
            await asyncio.to_thread(self.exchange.close)
        
        self._connected = False
        logger.info("Exchange adapter closed")
    
    async def __aenter__(self):
        """Context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        await self.close()
    
    def _normalize_timestamp(self, timestamp: Optional[int]) -> Optional[int]:
        """
        Normalize timestamp to milliseconds.
        
        Args:
            timestamp: Timestamp in seconds or milliseconds
            
        Returns:
            Timestamp in milliseconds or None
        """
        if timestamp is None:
            return None
        
        # If timestamp looks like seconds (< year 3000 in seconds), convert to ms
        if timestamp < 32503680000:
            return int(timestamp * 1000)
        
        return int(timestamp)
    
    def _normalize_ticker(self, ticker: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize ticker data with timestamp in milliseconds."""
        if ticker and "timestamp" in ticker:
            ticker["timestamp"] = self._normalize_timestamp(ticker["timestamp"])
        return ticker
    
    def _normalize_order_book(self, orderbook: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize order book data with timestamp in milliseconds."""
        if orderbook and "timestamp" in orderbook:
            orderbook["timestamp"] = self._normalize_timestamp(orderbook["timestamp"])
        return orderbook
    
    def _normalize_trade(self, trade: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize trade data with timestamp in milliseconds."""
        if trade:
            if "timestamp" in trade:
                trade["timestamp"] = self._normalize_timestamp(trade["timestamp"])
            if "datetime" in trade:
                # Keep datetime as-is (ISO format string)
                pass
        return trade
    
    def _normalize_ohlcv(self, ohlcv: List) -> List:
        """Normalize OHLCV data with timestamp in milliseconds."""
        if ohlcv and len(ohlcv) > 0:
            # OHLCV format: [timestamp, open, high, low, close, volume]
            ohlcv[0] = self._normalize_timestamp(ohlcv[0])
        return ohlcv
    
    async def _retry_with_backoff(
        self, 
        coro, 
        operation_name: str,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute coroutine with exponential backoff retry logic.
        
        Args:
            coro: Coroutine function to execute
            operation_name: Name of the operation for logging
            *args: Positional arguments for the coroutine
            **kwargs: Keyword arguments for the coroutine
            
        Returns:
            Result from the coroutine
            
        Raises:
            Exception: If all retries are exhausted
        """
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                return await coro(*args, **kwargs)
            except Exception as e:
                last_exception = e
                
                if attempt < self.max_retries - 1:
                    # Calculate backoff delay
                    backoff = min(
                        self.base_backoff * (2 ** attempt),
                        self.max_backoff
                    )
                    
                    logger.warning(
                        f"{operation_name} failed (attempt {attempt + 1}/{self.max_retries}): {e}. "
                        f"Retrying in {backoff:.1f}s..."
                    )
                    
                    await asyncio.sleep(backoff)
                else:
                    logger.error(
                        f"{operation_name} failed after {self.max_retries} attempts: {e}"
                    )
        
        raise last_exception
    
    # ========================================================================
    # WebSocket Watchers (ccxt.pro)
    # ========================================================================
    
    async def watch_ticker(self, symbol: str) -> Dict[str, Any]:
        """
        Watch ticker updates via WebSocket.
        
        Args:
            symbol: Trading pair symbol (e.g., "BTC/USDT:USDT")
            
        Returns:
            Ticker data with normalized timestamp in milliseconds
        """
        async def _watch():
            ticker = await self.exchange_pro.watch_ticker(symbol)
            return self._normalize_ticker(ticker)
        
        return await self._retry_with_backoff(
            _watch,
            f"watch_ticker({symbol})"
        )
    
    async def watch_order_book(
        self, 
        symbol: str, 
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Watch order book updates via WebSocket.
        
        Args:
            symbol: Trading pair symbol (e.g., "BTC/USDT:USDT")
            limit: Order book depth limit (optional)
            
        Returns:
            Order book data with normalized timestamp in milliseconds
        """
        async def _watch():
            orderbook = await self.exchange_pro.watch_order_book(symbol, limit)
            return self._normalize_order_book(orderbook)
        
        return await self._retry_with_backoff(
            _watch,
            f"watch_order_book({symbol}, limit={limit})"
        )
    
    async def watch_trades(self, symbol: str) -> List[Dict[str, Any]]:
        """
        Watch trades via WebSocket.
        
        Args:
            symbol: Trading pair symbol (e.g., "BTC/USDT:USDT")
            
        Returns:
            List of trade data with normalized timestamps in milliseconds
        """
        async def _watch():
            trades = await self.exchange_pro.watch_trades(symbol)
            return [self._normalize_trade(trade) for trade in trades]
        
        return await self._retry_with_backoff(
            _watch,
            f"watch_trades({symbol})"
        )
    
    async def watch_ohlcv(
        self, 
        symbol: str, 
        timeframe: str = "1m",
        since: Optional[int] = None,
        limit: Optional[int] = None
    ) -> List[List]:
        """
        Watch OHLCV (candlestick) updates via WebSocket.
        
        Args:
            symbol: Trading pair symbol (e.g., "BTC/USDT:USDT")
            timeframe: Timeframe (e.g., "1m", "5m", "1h")
            since: Timestamp in milliseconds (optional)
            limit: Number of candles (optional)
            
        Returns:
            List of OHLCV arrays with normalized timestamps in milliseconds
            Format: [[timestamp, open, high, low, close, volume], ...]
        """
        async def _watch():
            ohlcv_list = await self.exchange_pro.watch_ohlcv(
                symbol, 
                timeframe, 
                since, 
                limit
            )
            return [self._normalize_ohlcv(ohlcv) for ohlcv in ohlcv_list]
        
        return await self._retry_with_backoff(
            _watch,
            f"watch_ohlcv({symbol}, {timeframe})"
        )
    
    # ========================================================================
    # Funding Rate and Mark Price
    # ========================================================================
    
    async def fetch_funding_rate(self, symbol: str) -> Dict[str, Any]:
        """
        Fetch current funding rate for perpetual futures.
        
        Args:
            symbol: Trading pair symbol (e.g., "BTC/USDT:USDT")
            
        Returns:
            Funding rate data with normalized timestamps
        """
        async def _fetch():
            funding_rate = await asyncio.to_thread(
                self.exchange.fetch_funding_rate,
                symbol
            )
            
            # Normalize timestamps in funding rate data
            if funding_rate:
                if "timestamp" in funding_rate:
                    funding_rate["timestamp"] = self._normalize_timestamp(
                        funding_rate["timestamp"]
                    )
                if "fundingTimestamp" in funding_rate:
                    funding_rate["fundingTimestamp"] = self._normalize_timestamp(
                        funding_rate["fundingTimestamp"]
                    )
            
            return funding_rate
        
        return await self._retry_with_backoff(
            _fetch,
            f"fetch_funding_rate({symbol})"
        )
    
    async def fetch_funding_rate_history(
        self, 
        symbol: str,
        since: Optional[int] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch historical funding rates.
        
        Args:
            symbol: Trading pair symbol
            since: Timestamp in milliseconds
            limit: Number of records
            
        Returns:
            List of funding rate records with normalized timestamps
        """
        async def _fetch():
            history = await asyncio.to_thread(
                self.exchange.fetch_funding_rate_history,
                symbol,
                since,
                limit
            )
            
            # Normalize timestamps
            for record in history:
                if "timestamp" in record:
                    record["timestamp"] = self._normalize_timestamp(
                        record["timestamp"]
                    )
            
            return history
        
        return await self._retry_with_backoff(
            _fetch,
            f"fetch_funding_rate_history({symbol})"
        )
    
    async def derive_mark_price(self, symbol: str) -> Optional[float]:
        """
        Derive mark price from ticker data.
        
        Mark price is typically used for liquidation calculations in futures.
        Different exchanges may provide this differently.
        
        Args:
            symbol: Trading pair symbol (e.g., "BTC/USDT:USDT")
            
        Returns:
            Mark price as float, or None if not available
        """
        try:
            # Try to get ticker which may contain mark price
            ticker = await self.watch_ticker(symbol)
            
            # Check for mark price in ticker info
            if ticker and "info" in ticker:
                info = ticker["info"]
                
                # Bybit includes markPrice in ticker info
                if "markPrice" in info:
                    return float(info["markPrice"])
                elif "mark_price" in info:
                    return float(info["mark_price"])
            
            # Fallback: use last price if mark price not available
            if ticker and "last" in ticker:
                logger.debug(
                    f"Mark price not available for {symbol}, using last price"
                )
                return float(ticker["last"])
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to derive mark price for {symbol}: {e}")
            return None
    
    # ========================================================================
    # REST Fallback Methods
    # ========================================================================
    
    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1m",
        since: Optional[int] = None,
        limit: Optional[int] = None
    ) -> List[List]:
        """
        Fetch OHLCV data via REST API (fallback).
        
        Args:
            symbol: Trading pair symbol
            timeframe: Timeframe (e.g., "1m", "5m", "1h")
            since: Timestamp in milliseconds
            limit: Number of candles
            
        Returns:
            List of OHLCV arrays with normalized timestamps
        """
        async def _fetch():
            ohlcv_list = await asyncio.to_thread(
                self.exchange.fetch_ohlcv,
                symbol,
                timeframe,
                since,
                limit
            )
            return [self._normalize_ohlcv(ohlcv) for ohlcv in ohlcv_list]
        
        return await self._retry_with_backoff(
            _fetch,
            f"fetch_ohlcv({symbol}, {timeframe})"
        )
    
    async def fetch_ticker(self, symbol: str) -> Dict[str, Any]:
        """
        Fetch ticker via REST API (fallback).
        
        Args:
            symbol: Trading pair symbol
            
        Returns:
            Ticker data with normalized timestamp
        """
        async def _fetch():
            ticker = await asyncio.to_thread(
                self.exchange.fetch_ticker,
                symbol
            )
            return self._normalize_ticker(ticker)
        
        return await self._retry_with_backoff(
            _fetch,
            f"fetch_ticker({symbol})"
        )
    
    async def fetch_order_book(
        self, 
        symbol: str, 
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Fetch order book via REST API (fallback).
        
        Args:
            symbol: Trading pair symbol
            limit: Order book depth limit
            
        Returns:
            Order book data with normalized timestamp
        """
        async def _fetch():
            orderbook = await asyncio.to_thread(
                self.exchange.fetch_order_book,
                symbol,
                limit
            )
            return self._normalize_order_book(orderbook)
        
        return await self._retry_with_backoff(
            _fetch,
            f"fetch_order_book({symbol})"
        )
    
    async def fetch_trades(
        self, 
        symbol: str,
        since: Optional[int] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch trades via REST API (fallback).
        
        Args:
            symbol: Trading pair symbol
            since: Timestamp in milliseconds
            limit: Number of trades
            
        Returns:
            List of trade data with normalized timestamps
        """
        async def _fetch():
            trades = await asyncio.to_thread(
                self.exchange.fetch_trades,
                symbol,
                since,
                limit
            )
            return [self._normalize_trade(trade) for trade in trades]
        
        return await self._retry_with_backoff(
            _fetch,
            f"fetch_trades({symbol})"
        )
    
    # ========================================================================
    # Utility Methods
    # ========================================================================
    
    async def load_markets(self, reload: bool = False) -> Dict[str, Any]:
        """
        Load exchange markets metadata.
        
        Args:
            reload: Force reload markets from exchange
            
        Returns:
            Dictionary of market metadata
        """
        return await asyncio.to_thread(
            self.exchange.load_markets,
            reload
        )
    
    def get_market_symbol(self, base: str, quote: str) -> str:
        """
        Construct market symbol in exchange format.
        
        Args:
            base: Base currency (e.g., "BTC")
            quote: Quote currency (e.g., "USDT")
            
        Returns:
            Formatted symbol (e.g., "BTC/USDT:USDT" for swap)
        """
        if self.default_type == "swap":
            # Perpetual futures format
            return f"{base}/{quote}:{quote}"
        else:
            # Spot format
            return f"{base}/{quote}"


# ============================================================================
# Factory function for easy initialization
# ============================================================================

def create_exchange_adapter(
    exchange_name: str = "bybit",
    default_type: str = "swap",
    sandbox: bool = False,
    api_key: Optional[str] = None,
    secret: Optional[str] = None,
    **options
) -> ExchangeAdapter:
    """
    Factory function to create an exchange adapter instance.
    
    Args:
        exchange_name: Name of the exchange
        default_type: Market type (swap, spot, future)
        sandbox: Enable sandbox/testnet mode
        api_key: API key (optional)
        secret: API secret (optional)
        **options: Additional exchange options
        
    Returns:
        Configured ExchangeAdapter instance
    """
    return ExchangeAdapter(
        exchange_name=exchange_name,
        default_type=default_type,
        sandbox=sandbox,
        api_key=api_key,
        secret=secret,
        options=options if options else None
    )


__all__ = [
    "ExchangeAdapter",
    "create_exchange_adapter",
]
