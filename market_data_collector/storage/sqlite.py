"""SQLite storage backend for per-symbol market data with retention policy."""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Schema version for migrations
SCHEMA_VERSION = 1

# Retention period in days
RETENTION_DAYS = 7


class SQLiteStorage:
    """Manages per-symbol SQLite databases with WAL mode and retention policies.
    
    Each symbol gets its own database file for better concurrency and isolation.
    All tables include timestamp indices for efficient time-based queries and cleanup.
    """

    def __init__(self, base_path: str | Path, symbol: str) -> None:
        """Initialize SQLite storage for a specific symbol.
        
        Args:
            base_path: Base directory path for storing database files
            symbol: Trading pair symbol (e.g., 'BTCUSDT')
        """
        self.base_path = Path(base_path)
        self.symbol = symbol
        self.db_path = self._get_db_path()
        
        # Ensure storage directory exists
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize database with schema and WAL mode
        self._initialize_database()
        
        logger.info(f"SQLite storage initialized for {symbol} at {self.db_path}")

    def _get_db_path(self) -> Path:
        """Get the database file path for this symbol."""
        # Sanitize symbol name for filesystem
        safe_symbol = self.symbol.replace("/", "_").replace(":", "_")
        return self.base_path / f"{safe_symbol}.db"

    def _get_connection(self) -> sqlite3.Connection:
        """Create a new database connection with optimal settings."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row  # Enable dict-like row access
        return conn

    def _initialize_database(self) -> None:
        """Initialize database schema and enable WAL mode."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Enable WAL (Write-Ahead Logging) mode for better concurrency
            cursor.execute("PRAGMA journal_mode=WAL")
            
            # Create schema version table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS _schema_version (
                    version INTEGER PRIMARY KEY,
                    applied_at INTEGER NOT NULL
                )
            """)
            
            # Check current schema version
            cursor.execute("SELECT version FROM _schema_version ORDER BY version DESC LIMIT 1")
            result = cursor.fetchone()
            current_version = result[0] if result else 0
            
            # Apply migrations if needed
            if current_version < SCHEMA_VERSION:
                self._apply_migrations(conn, current_version)
            
            conn.commit()
            
            # Checkpoint WAL to ensure schema is visible to other connections
            cursor.execute("PRAGMA wal_checkpoint(FULL)")

    def _apply_migrations(self, conn: sqlite3.Connection, from_version: int) -> None:
        """Apply database schema migrations."""
        cursor = conn.cursor()
        
        if from_version < 1:
            logger.info(f"Applying schema migration v1 for {self.symbol}")
            
            # Ticker table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ticker (
                    timestamp INTEGER NOT NULL,
                    symbol TEXT NOT NULL,
                    high REAL,
                    low REAL,
                    bid REAL,
                    bid_volume REAL,
                    ask REAL,
                    ask_volume REAL,
                    vwap REAL,
                    open REAL,
                    close REAL,
                    last REAL,
                    previous_close REAL,
                    change REAL,
                    percentage REAL,
                    average REAL,
                    base_volume REAL,
                    quote_volume REAL,
                    info TEXT
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_ticker_timestamp ON ticker(timestamp)")
            
            # Orderbook snapshots table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS orderbook (
                    timestamp INTEGER NOT NULL,
                    symbol TEXT NOT NULL,
                    bids TEXT NOT NULL,
                    asks TEXT NOT NULL,
                    nonce INTEGER,
                    datetime TEXT
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_orderbook_timestamp ON orderbook(timestamp)")
            
            # Trades table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id TEXT PRIMARY KEY,
                    timestamp INTEGER NOT NULL,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    price REAL NOT NULL,
                    amount REAL NOT NULL,
                    cost REAL,
                    order_id TEXT,
                    taker_or_maker TEXT,
                    fee_cost REAL,
                    fee_currency TEXT,
                    info TEXT
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades(timestamp)")
            
            # OHLCV table (supports multiple timeframes)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ohlcv (
                    timestamp INTEGER NOT NULL,
                    symbol TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    open REAL NOT NULL,
                    high REAL NOT NULL,
                    low REAL NOT NULL,
                    close REAL NOT NULL,
                    volume REAL NOT NULL,
                    PRIMARY KEY (timestamp, timeframe)
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_ohlcv_timestamp ON ohlcv(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_ohlcv_timeframe ON ohlcv(timeframe)")
            
            # Funding rate table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS funding_rate (
                    timestamp INTEGER NOT NULL PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    funding_rate REAL NOT NULL,
                    funding_timestamp INTEGER,
                    info TEXT
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_funding_timestamp ON funding_rate(timestamp)")
            
            # Mark price table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS mark_price (
                    timestamp INTEGER NOT NULL PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    mark_price REAL NOT NULL,
                    index_price REAL,
                    info TEXT
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_mark_price_timestamp ON mark_price(timestamp)")
            
            # Record migration
            cursor.execute(
                "INSERT INTO _schema_version (version, applied_at) VALUES (?, ?)",
                (1, int(datetime.now().timestamp() * 1000))
            )

    def _cleanup_old_records(self, conn: sqlite3.Connection) -> None:
        """Delete records older than retention period from all tables."""
        cursor = conn.cursor()
        cutoff_timestamp = int((datetime.now() - timedelta(days=RETENTION_DAYS)).timestamp() * 1000)
        
        tables = ["ticker", "orderbook", "trades", "ohlcv", "funding_rate", "mark_price"]
        
        for table in tables:
            cursor.execute(f"DELETE FROM {table} WHERE timestamp < ?", (cutoff_timestamp,))
            deleted = cursor.rowcount
            if deleted > 0:
                logger.debug(f"Deleted {deleted} old records from {table} for {self.symbol}")

    def insert_ticker(self, data: dict[str, Any]) -> None:
        """Insert ticker data with retention cleanup.
        
        Args:
            data: Ticker data in ccxt format
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO ticker (
                    timestamp, symbol, high, low, bid, bid_volume, ask, ask_volume,
                    vwap, open, close, last, previous_close, change, percentage,
                    average, base_volume, quote_volume, info
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data.get("timestamp"),
                data.get("symbol"),
                data.get("high"),
                data.get("low"),
                data.get("bid"),
                data.get("bidVolume"),
                data.get("ask"),
                data.get("askVolume"),
                data.get("vwap"),
                data.get("open"),
                data.get("close"),
                data.get("last"),
                data.get("previousClose"),
                data.get("change"),
                data.get("percentage"),
                data.get("average"),
                data.get("baseVolume"),
                data.get("quoteVolume"),
                str(data.get("info", {}))
            ))
            
            self._cleanup_old_records(conn)
            conn.commit()

    def insert_orderbook(self, data: dict[str, Any]) -> None:
        """Insert orderbook snapshot with retention cleanup.
        
        Args:
            data: Orderbook data in ccxt format
        """
        import json
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO orderbook (
                    timestamp, symbol, bids, asks, nonce, datetime
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                data.get("timestamp"),
                data.get("symbol"),
                json.dumps(data.get("bids", [])),
                json.dumps(data.get("asks", [])),
                data.get("nonce"),
                data.get("datetime")
            ))
            
            self._cleanup_old_records(conn)
            conn.commit()

    def insert_trades(self, trades: list[dict[str, Any]]) -> int:
        """Bulk insert trades with retention cleanup.
        
        Args:
            trades: List of trade data in ccxt format
            
        Returns:
            Number of trades successfully inserted
        """
        if not trades:
            return 0
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            inserted = 0
            
            for trade in trades:
                try:
                    cursor.execute("""
                        INSERT OR IGNORE INTO trades (
                            id, timestamp, symbol, side, price, amount, cost,
                            order_id, taker_or_maker, fee_cost, fee_currency, info
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        trade.get("id"),
                        trade.get("timestamp"),
                        trade.get("symbol"),
                        trade.get("side"),
                        trade.get("price"),
                        trade.get("amount"),
                        trade.get("cost"),
                        trade.get("order"),
                        trade.get("takerOrMaker"),
                        trade.get("fee", {}).get("cost"),
                        trade.get("fee", {}).get("currency"),
                        str(trade.get("info", {}))
                    ))
                    if cursor.rowcount > 0:
                        inserted += 1
                except sqlite3.IntegrityError:
                    # Trade already exists, skip
                    pass
            
            self._cleanup_old_records(conn)
            conn.commit()
            return inserted

    def insert_ohlcv(self, timeframe: str, ohlcv_data: list[list]) -> int:
        """Bulk insert OHLCV candles with retention cleanup.
        
        Args:
            timeframe: Timeframe string (e.g., '1m', '5m', '1h')
            ohlcv_data: List of OHLCV arrays [timestamp, open, high, low, close, volume]
            
        Returns:
            Number of candles successfully inserted
        """
        if not ohlcv_data:
            return 0
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            inserted = 0
            
            for candle in ohlcv_data:
                try:
                    cursor.execute("""
                        INSERT OR REPLACE INTO ohlcv (
                            timestamp, symbol, timeframe, open, high, low, close, volume
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        candle[0],
                        self.symbol,
                        timeframe,
                        candle[1],
                        candle[2],
                        candle[3],
                        candle[4],
                        candle[5]
                    ))
                    if cursor.rowcount > 0:
                        inserted += 1
                except sqlite3.IntegrityError:
                    pass
            
            self._cleanup_old_records(conn)
            conn.commit()
            return inserted

    def insert_funding_rate(self, data: dict[str, Any]) -> None:
        """Insert funding rate data with retention cleanup.
        
        Args:
            data: Funding rate data in ccxt format
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO funding_rate (
                    timestamp, symbol, funding_rate, funding_timestamp, info
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                data.get("timestamp"),
                data.get("symbol"),
                data.get("fundingRate"),
                data.get("fundingTimestamp"),
                str(data.get("info", {}))
            ))
            
            self._cleanup_old_records(conn)
            conn.commit()

    def insert_mark_price(self, data: dict[str, Any]) -> None:
        """Insert mark price data with retention cleanup.
        
        Args:
            data: Mark price data in ccxt format
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO mark_price (
                    timestamp, symbol, mark_price, index_price, info
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                data.get("timestamp"),
                data.get("symbol"),
                data.get("markPrice"),
                data.get("indexPrice"),
                str(data.get("info", {}))
            ))
            
            self._cleanup_old_records(conn)
            conn.commit()

    def query_ticker(
        self,
        start_time: int | None = None,
        end_time: int | None = None,
        limit: int | None = None
    ) -> list[dict[str, Any]]:
        """Query ticker data within time range.
        
        Args:
            start_time: Start timestamp in milliseconds (inclusive)
            end_time: End timestamp in milliseconds (inclusive)
            limit: Maximum number of records to return
            
        Returns:
            List of ticker records in ccxt-like format
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            query = "SELECT * FROM ticker WHERE 1=1"
            params = []
            
            if start_time is not None:
                query += " AND timestamp >= ?"
                params.append(start_time)
            
            if end_time is not None:
                query += " AND timestamp <= ?"
                params.append(end_time)
            
            query += " ORDER BY timestamp DESC"
            
            if limit is not None:
                query += " LIMIT ?"
                params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            return [self._row_to_ticker(row) for row in rows]

    def query_orderbook(
        self,
        start_time: int | None = None,
        end_time: int | None = None,
        limit: int | None = None
    ) -> list[dict[str, Any]]:
        """Query orderbook snapshots within time range.
        
        Args:
            start_time: Start timestamp in milliseconds (inclusive)
            end_time: End timestamp in milliseconds (inclusive)
            limit: Maximum number of records to return
            
        Returns:
            List of orderbook records in ccxt-like format
        """
        import json
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            query = "SELECT * FROM orderbook WHERE 1=1"
            params = []
            
            if start_time is not None:
                query += " AND timestamp >= ?"
                params.append(start_time)
            
            if end_time is not None:
                query += " AND timestamp <= ?"
                params.append(end_time)
            
            query += " ORDER BY timestamp DESC"
            
            if limit is not None:
                query += " LIMIT ?"
                params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            results = []
            for row in rows:
                results.append({
                    "timestamp": row["timestamp"],
                    "symbol": row["symbol"],
                    "bids": json.loads(row["bids"]),
                    "asks": json.loads(row["asks"]),
                    "nonce": row["nonce"],
                    "datetime": row["datetime"]
                })
            
            return results

    def query_trades(
        self,
        start_time: int | None = None,
        end_time: int | None = None,
        limit: int | None = None
    ) -> list[dict[str, Any]]:
        """Query trades within time range.
        
        Args:
            start_time: Start timestamp in milliseconds (inclusive)
            end_time: End timestamp in milliseconds (inclusive)
            limit: Maximum number of records to return
            
        Returns:
            List of trade records in ccxt-like format
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            query = "SELECT * FROM trades WHERE 1=1"
            params = []
            
            if start_time is not None:
                query += " AND timestamp >= ?"
                params.append(start_time)
            
            if end_time is not None:
                query += " AND timestamp <= ?"
                params.append(end_time)
            
            query += " ORDER BY timestamp DESC"
            
            if limit is not None:
                query += " LIMIT ?"
                params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            return [self._row_to_trade(row) for row in rows]

    def query_ohlcv(
        self,
        timeframe: str,
        start_time: int | None = None,
        end_time: int | None = None,
        limit: int | None = None
    ) -> list[list]:
        """Query OHLCV candles for a specific timeframe.
        
        Args:
            timeframe: Timeframe string (e.g., '1m', '5m', '1h')
            start_time: Start timestamp in milliseconds (inclusive)
            end_time: End timestamp in milliseconds (inclusive)
            limit: Maximum number of records to return
            
        Returns:
            List of OHLCV arrays [timestamp, open, high, low, close, volume]
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            query = "SELECT * FROM ohlcv WHERE timeframe = ?"
            params = [timeframe]
            
            if start_time is not None:
                query += " AND timestamp >= ?"
                params.append(start_time)
            
            if end_time is not None:
                query += " AND timestamp <= ?"
                params.append(end_time)
            
            query += " ORDER BY timestamp ASC"
            
            if limit is not None:
                query += " LIMIT ?"
                params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            return [
                [row["timestamp"], row["open"], row["high"], row["low"], row["close"], row["volume"]]
                for row in rows
            ]

    def query_funding_rate(
        self,
        start_time: int | None = None,
        end_time: int | None = None,
        limit: int | None = None
    ) -> list[dict[str, Any]]:
        """Query funding rate data within time range.
        
        Args:
            start_time: Start timestamp in milliseconds (inclusive)
            end_time: End timestamp in milliseconds (inclusive)
            limit: Maximum number of records to return
            
        Returns:
            List of funding rate records in ccxt-like format
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            query = "SELECT * FROM funding_rate WHERE 1=1"
            params = []
            
            if start_time is not None:
                query += " AND timestamp >= ?"
                params.append(start_time)
            
            if end_time is not None:
                query += " AND timestamp <= ?"
                params.append(end_time)
            
            query += " ORDER BY timestamp DESC"
            
            if limit is not None:
                query += " LIMIT ?"
                params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            return [self._row_to_funding_rate(row) for row in rows]

    def query_mark_price(
        self,
        start_time: int | None = None,
        end_time: int | None = None,
        limit: int | None = None
    ) -> list[dict[str, Any]]:
        """Query mark price data within time range.
        
        Args:
            start_time: Start timestamp in milliseconds (inclusive)
            end_time: End timestamp in milliseconds (inclusive)
            limit: Maximum number of records to return
            
        Returns:
            List of mark price records in ccxt-like format
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            query = "SELECT * FROM mark_price WHERE 1=1"
            params = []
            
            if start_time is not None:
                query += " AND timestamp >= ?"
                params.append(start_time)
            
            if end_time is not None:
                query += " AND timestamp <= ?"
                params.append(end_time)
            
            query += " ORDER BY timestamp DESC"
            
            if limit is not None:
                query += " LIMIT ?"
                params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            return [self._row_to_mark_price(row) for row in rows]

    def _row_to_ticker(self, row: sqlite3.Row) -> dict[str, Any]:
        """Convert database row to ccxt ticker format."""
        return {
            "timestamp": row["timestamp"],
            "symbol": row["symbol"],
            "high": row["high"],
            "low": row["low"],
            "bid": row["bid"],
            "bidVolume": row["bid_volume"],
            "ask": row["ask"],
            "askVolume": row["ask_volume"],
            "vwap": row["vwap"],
            "open": row["open"],
            "close": row["close"],
            "last": row["last"],
            "previousClose": row["previous_close"],
            "change": row["change"],
            "percentage": row["percentage"],
            "average": row["average"],
            "baseVolume": row["base_volume"],
            "quoteVolume": row["quote_volume"],
            "info": row["info"]
        }

    def _row_to_trade(self, row: sqlite3.Row) -> dict[str, Any]:
        """Convert database row to ccxt trade format."""
        result = {
            "id": row["id"],
            "timestamp": row["timestamp"],
            "symbol": row["symbol"],
            "side": row["side"],
            "price": row["price"],
            "amount": row["amount"],
            "cost": row["cost"],
            "order": row["order_id"],
            "takerOrMaker": row["taker_or_maker"],
            "info": row["info"]
        }
        
        if row["fee_cost"] is not None or row["fee_currency"] is not None:
            result["fee"] = {
                "cost": row["fee_cost"],
                "currency": row["fee_currency"]
            }
        
        return result

    def _row_to_funding_rate(self, row: sqlite3.Row) -> dict[str, Any]:
        """Convert database row to ccxt funding rate format."""
        return {
            "timestamp": row["timestamp"],
            "symbol": row["symbol"],
            "fundingRate": row["funding_rate"],
            "fundingTimestamp": row["funding_timestamp"],
            "info": row["info"]
        }

    def _row_to_mark_price(self, row: sqlite3.Row) -> dict[str, Any]:
        """Convert database row to ccxt mark price format."""
        return {
            "timestamp": row["timestamp"],
            "symbol": row["symbol"],
            "markPrice": row["mark_price"],
            "indexPrice": row["index_price"],
            "info": row["info"]
        }

    def close(self) -> None:
        """Close database connection and perform cleanup."""
        # Connections are closed automatically via context manager
        # This method is for compatibility and future extensions
        pass
