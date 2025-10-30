"""Unit tests for SQLite storage backend with retention policy."""

import json
import sqlite3
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from market_data_collector.storage.sqlite import RETENTION_DAYS, SQLiteStorage


@pytest.fixture
def temp_storage_dir():
    """Create a temporary directory for test databases."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def storage(temp_storage_dir):
    """Create a SQLite storage instance for testing."""
    return SQLiteStorage(temp_storage_dir, "BTCUSDT")


class TestInitialization:
    """Test database initialization and configuration."""

    def test_creates_database_file(self, temp_storage_dir):
        """Test that database file is created."""
        storage = SQLiteStorage(temp_storage_dir, "BTCUSDT")
        assert storage.db_path.exists()
        assert storage.db_path.name == "BTCUSDT.db"

    def test_creates_storage_directory(self):
        """Test that storage directory is created if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "nested" / "storage"
            storage = SQLiteStorage(storage_path, "ETHUSDT")
            assert storage_path.exists()
            assert storage.db_path.exists()

    def test_sanitizes_symbol_name(self, temp_storage_dir):
        """Test that symbol names are sanitized for filesystem."""
        storage = SQLiteStorage(temp_storage_dir, "BTC/USDT:USDT")
        assert storage.db_path.name == "BTC_USDT_USDT.db"

    def test_enables_wal_mode(self, storage):
        """Test that WAL mode is enabled."""
        with storage._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA journal_mode")
            result = cursor.fetchone()
            assert result[0].lower() == "wal"

    def test_creates_all_tables(self, storage):
        """Test that all required tables are created."""
        with storage._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name NOT LIKE '\\_%' ESCAPE '\\'
                ORDER BY name
            """)
            tables = [row[0] for row in cursor.fetchall()]
            
            expected_tables = [
                "ticker",
                "orderbook",
                "trades",
                "ohlcv",
                "funding_rate",
                "mark_price"
            ]
            
            for table in expected_tables:
                assert table in tables, f"Table {table} not created"

    def test_creates_timestamp_indices(self, storage):
        """Test that timestamp indices are created for all tables."""
        with storage._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='index' AND name LIKE 'idx_%timestamp'
            """)
            indices = [row[0] for row in cursor.fetchall()]
            
            expected_indices = [
                "idx_ticker_timestamp",
                "idx_orderbook_timestamp",
                "idx_trades_timestamp",
                "idx_ohlcv_timestamp",
                "idx_funding_timestamp",
                "idx_mark_price_timestamp"
            ]
            
            for index in expected_indices:
                assert index in indices, f"Index {index} not created"

    def test_records_schema_version(self, storage):
        """Test that schema version is recorded."""
        with storage._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT version FROM _schema_version")
            result = cursor.fetchone()
            assert result is not None
            assert result[0] == 1


class TestTickerOperations:
    """Test ticker data insertion and querying."""

    def test_insert_and_query_ticker(self, storage):
        """Test inserting and querying ticker data."""
        now = int(datetime.now().timestamp() * 1000)
        ticker_data = {
            "timestamp": now,
            "symbol": "BTCUSDT",
            "high": 50000.0,
            "low": 48000.0,
            "bid": 49500.0,
            "bidVolume": 1.5,
            "ask": 49501.0,
            "askVolume": 2.0,
            "vwap": 49250.0,
            "open": 48500.0,
            "close": 49500.0,
            "last": 49500.0,
            "previousClose": 48500.0,
            "change": 1000.0,
            "percentage": 2.06,
            "average": 49000.0,
            "baseVolume": 1000.0,
            "quoteVolume": 49250000.0,
            "info": {"extra": "data"}
        }
        
        storage.insert_ticker(ticker_data)
        
        results = storage.query_ticker()
        assert len(results) == 1
        
        result = results[0]
        assert result["timestamp"] == now
        assert result["symbol"] == "BTCUSDT"
        assert result["high"] == 50000.0
        assert result["low"] == 48000.0
        assert result["bid"] == 49500.0
        assert result["last"] == 49500.0

    def test_query_ticker_with_time_range(self, storage):
        """Test querying ticker data with time range."""
        base_time = int(datetime.now().timestamp() * 1000)
        
        # Insert three tickers at different times
        for i in range(3):
            ticker = {
                "timestamp": base_time + (i * 1000),
                "symbol": "BTCUSDT",
                "last": 49000.0 + i
            }
            storage.insert_ticker(ticker)
        
        # Query with time range (inclusive on both ends)
        results = storage.query_ticker(
            start_time=base_time + 1000,
            end_time=base_time + 2000
        )
        
        # Should return 2 results (at +1000 and +2000)
        assert len(results) == 2
        assert results[0]["last"] == 49002.0  # DESC order
        assert results[1]["last"] == 49001.0

    def test_query_ticker_with_limit(self, storage):
        """Test querying ticker data with limit."""
        base_time = int(datetime.now().timestamp() * 1000)
        
        # Insert five tickers
        for i in range(5):
            ticker = {
                "timestamp": base_time + (i * 1000),
                "symbol": "BTCUSDT",
                "last": 49000.0 + i
            }
            storage.insert_ticker(ticker)
        
        # Query with limit
        results = storage.query_ticker(limit=3)
        assert len(results) == 3


class TestOrderbookOperations:
    """Test orderbook data insertion and querying."""

    def test_insert_and_query_orderbook(self, storage):
        """Test inserting and querying orderbook data."""
        now = int(datetime.now().timestamp() * 1000)
        orderbook_data = {
            "timestamp": now,
            "symbol": "BTCUSDT",
            "bids": [[49500.0, 1.5], [49499.0, 2.0]],
            "asks": [[49501.0, 1.2], [49502.0, 1.8]],
            "nonce": 12345,
            "datetime": datetime.fromtimestamp(now / 1000).isoformat()
        }
        
        storage.insert_orderbook(orderbook_data)
        
        results = storage.query_orderbook()
        assert len(results) == 1
        
        result = results[0]
        assert result["timestamp"] == now
        assert result["symbol"] == "BTCUSDT"
        assert len(result["bids"]) == 2
        assert len(result["asks"]) == 2
        assert result["bids"][0] == [49500.0, 1.5]
        assert result["asks"][0] == [49501.0, 1.2]

    def test_query_orderbook_with_time_range(self, storage):
        """Test querying orderbook with time range."""
        base_time = int(datetime.now().timestamp() * 1000)
        
        for i in range(3):
            orderbook = {
                "timestamp": base_time + (i * 1000),
                "symbol": "BTCUSDT",
                "bids": [[49500.0 + i, 1.0]],
                "asks": [[49501.0 + i, 1.0]]
            }
            storage.insert_orderbook(orderbook)
        
        results = storage.query_orderbook(
            start_time=base_time + 1000,
            end_time=base_time + 1000
        )
        
        assert len(results) == 1


class TestTradesOperations:
    """Test trades data insertion and querying."""

    def test_insert_and_query_trades(self, storage):
        """Test bulk inserting and querying trades."""
        now = int(datetime.now().timestamp() * 1000)
        trades_data = [
            {
                "id": "trade1",
                "timestamp": now,
                "symbol": "BTCUSDT",
                "side": "buy",
                "price": 49500.0,
                "amount": 0.5,
                "cost": 24750.0,
                "order": "order123",
                "takerOrMaker": "taker",
                "fee": {"cost": 0.001, "currency": "USDT"},
                "info": {}
            },
            {
                "id": "trade2",
                "timestamp": now + 1000,
                "symbol": "BTCUSDT",
                "side": "sell",
                "price": 49600.0,
                "amount": 0.3,
                "cost": 14880.0,
                "order": "order124",
                "takerOrMaker": "maker",
                "fee": {"cost": 0.0005, "currency": "USDT"},
                "info": {}
            }
        ]
        
        inserted = storage.insert_trades(trades_data)
        assert inserted == 2
        
        results = storage.query_trades()
        assert len(results) == 2
        
        # Results are ordered by timestamp DESC
        assert results[0]["id"] == "trade2"
        assert results[1]["id"] == "trade1"
        assert results[1]["price"] == 49500.0
        assert results[1]["side"] == "buy"

    def test_insert_duplicate_trades_ignored(self, storage):
        """Test that duplicate trades are ignored."""
        now = int(datetime.now().timestamp() * 1000)
        trade = {
            "id": "trade1",
            "timestamp": now,
            "symbol": "BTCUSDT",
            "side": "buy",
            "price": 49500.0,
            "amount": 0.5
        }
        
        inserted1 = storage.insert_trades([trade])
        assert inserted1 == 1
        
        inserted2 = storage.insert_trades([trade])
        assert inserted2 == 0
        
        results = storage.query_trades()
        assert len(results) == 1

    def test_query_trades_with_time_range(self, storage):
        """Test querying trades with time range."""
        base_time = int(datetime.now().timestamp() * 1000)
        
        trades = [
            {
                "id": f"trade{i}",
                "timestamp": base_time + (i * 1000),
                "symbol": "BTCUSDT",
                "side": "buy",
                "price": 49500.0 + i,
                "amount": 0.1
            }
            for i in range(5)
        ]
        
        storage.insert_trades(trades)
        
        results = storage.query_trades(
            start_time=base_time + 2000,
            end_time=base_time + 3000
        )
        
        assert len(results) == 2


class TestOHLCVOperations:
    """Test OHLCV data insertion and querying."""

    def test_insert_and_query_ohlcv(self, storage):
        """Test bulk inserting and querying OHLCV data."""
        now = int(datetime.now().timestamp() * 1000)
        ohlcv_data = [
            [now, 49000.0, 50000.0, 48500.0, 49500.0, 100.0],
            [now + 60000, 49500.0, 50500.0, 49000.0, 50000.0, 120.0],
            [now + 120000, 50000.0, 51000.0, 49800.0, 50800.0, 110.0]
        ]
        
        inserted = storage.insert_ohlcv("1m", ohlcv_data)
        assert inserted == 3
        
        results = storage.query_ohlcv("1m")
        assert len(results) == 3
        
        # Results are ordered by timestamp ASC
        assert results[0][0] == now
        assert results[0][1] == 49000.0  # open
        assert results[0][2] == 50000.0  # high
        assert results[0][3] == 48500.0  # low
        assert results[0][4] == 49500.0  # close
        assert results[0][5] == 100.0    # volume

    def test_insert_ohlcv_multiple_timeframes(self, storage):
        """Test inserting OHLCV data for multiple timeframes."""
        now = int(datetime.now().timestamp() * 1000)
        
        candles_1m = [[now, 49000.0, 50000.0, 48500.0, 49500.0, 100.0]]
        candles_5m = [[now, 48500.0, 50500.0, 48000.0, 50000.0, 500.0]]
        
        storage.insert_ohlcv("1m", candles_1m)
        storage.insert_ohlcv("5m", candles_5m)
        
        results_1m = storage.query_ohlcv("1m")
        results_5m = storage.query_ohlcv("5m")
        
        assert len(results_1m) == 1
        assert len(results_5m) == 1
        assert results_1m[0][5] == 100.0  # 1m volume
        assert results_5m[0][5] == 500.0  # 5m volume

    def test_insert_ohlcv_replace_existing(self, storage):
        """Test that duplicate OHLCV candles are replaced."""
        now = int(datetime.now().timestamp() * 1000)
        
        candle1 = [[now, 49000.0, 50000.0, 48500.0, 49500.0, 100.0]]
        candle2 = [[now, 49100.0, 50100.0, 48600.0, 49600.0, 105.0]]
        
        storage.insert_ohlcv("1m", candle1)
        storage.insert_ohlcv("1m", candle2)
        
        results = storage.query_ohlcv("1m")
        assert len(results) == 1
        assert results[0][1] == 49100.0  # Updated open

    def test_query_ohlcv_with_time_range(self, storage):
        """Test querying OHLCV with time range."""
        base_time = int(datetime.now().timestamp() * 1000)
        
        candles = [
            [base_time + (i * 60000), 49000.0 + i, 50000.0 + i, 48500.0 + i, 49500.0 + i, 100.0]
            for i in range(10)
        ]
        
        storage.insert_ohlcv("1m", candles)
        
        results = storage.query_ohlcv(
            "1m",
            start_time=base_time + 180000,
            end_time=base_time + 300000
        )
        
        assert len(results) == 3


class TestFundingRateOperations:
    """Test funding rate data insertion and querying."""

    def test_insert_and_query_funding_rate(self, storage):
        """Test inserting and querying funding rate data."""
        now = int(datetime.now().timestamp() * 1000)
        funding_data = {
            "timestamp": now,
            "symbol": "BTCUSDT",
            "fundingRate": 0.0001,
            "fundingTimestamp": now + 28800000,  # 8 hours later
            "info": {}
        }
        
        storage.insert_funding_rate(funding_data)
        
        results = storage.query_funding_rate()
        assert len(results) == 1
        
        result = results[0]
        assert result["timestamp"] == now
        assert result["symbol"] == "BTCUSDT"
        assert result["fundingRate"] == 0.0001

    def test_insert_funding_rate_replace_existing(self, storage):
        """Test that duplicate funding rates are replaced."""
        now = int(datetime.now().timestamp() * 1000)
        
        funding1 = {
            "timestamp": now,
            "symbol": "BTCUSDT",
            "fundingRate": 0.0001
        }
        
        funding2 = {
            "timestamp": now,
            "symbol": "BTCUSDT",
            "fundingRate": 0.0002
        }
        
        storage.insert_funding_rate(funding1)
        storage.insert_funding_rate(funding2)
        
        results = storage.query_funding_rate()
        assert len(results) == 1
        assert results[0]["fundingRate"] == 0.0002

    def test_query_funding_rate_with_time_range(self, storage):
        """Test querying funding rate with time range."""
        base_time = int(datetime.now().timestamp() * 1000)
        
        for i in range(3):
            funding = {
                "timestamp": base_time + (i * 28800000),  # 8-hour intervals
                "symbol": "BTCUSDT",
                "fundingRate": 0.0001 * (i + 1)
            }
            storage.insert_funding_rate(funding)
        
        results = storage.query_funding_rate(
            start_time=base_time + 28800000,
            end_time=base_time + 28800000
        )
        
        assert len(results) == 1
        assert results[0]["fundingRate"] == 0.0002


class TestMarkPriceOperations:
    """Test mark price data insertion and querying."""

    def test_insert_and_query_mark_price(self, storage):
        """Test inserting and querying mark price data."""
        now = int(datetime.now().timestamp() * 1000)
        mark_price_data = {
            "timestamp": now,
            "symbol": "BTCUSDT",
            "markPrice": 49500.0,
            "indexPrice": 49490.0,
            "info": {}
        }
        
        storage.insert_mark_price(mark_price_data)
        
        results = storage.query_mark_price()
        assert len(results) == 1
        
        result = results[0]
        assert result["timestamp"] == now
        assert result["symbol"] == "BTCUSDT"
        assert result["markPrice"] == 49500.0
        assert result["indexPrice"] == 49490.0

    def test_insert_mark_price_replace_existing(self, storage):
        """Test that duplicate mark prices are replaced."""
        now = int(datetime.now().timestamp() * 1000)
        
        mark_price1 = {
            "timestamp": now,
            "symbol": "BTCUSDT",
            "markPrice": 49500.0
        }
        
        mark_price2 = {
            "timestamp": now,
            "symbol": "BTCUSDT",
            "markPrice": 49600.0
        }
        
        storage.insert_mark_price(mark_price1)
        storage.insert_mark_price(mark_price2)
        
        results = storage.query_mark_price()
        assert len(results) == 1
        assert results[0]["markPrice"] == 49600.0

    def test_query_mark_price_with_time_range(self, storage):
        """Test querying mark price with time range."""
        base_time = int(datetime.now().timestamp() * 1000)
        
        for i in range(5):
            mark_price = {
                "timestamp": base_time + (i * 1000),
                "symbol": "BTCUSDT",
                "markPrice": 49500.0 + i
            }
            storage.insert_mark_price(mark_price)
        
        results = storage.query_mark_price(
            start_time=base_time + 2000,
            end_time=base_time + 4000
        )
        
        assert len(results) == 3


class TestRetentionPolicy:
    """Test retention policy and automatic cleanup of old records."""

    def test_cleanup_old_ticker_records(self, storage):
        """Test that old ticker records are deleted."""
        now = int(datetime.now().timestamp() * 1000)
        old_time = int((datetime.now() - timedelta(days=RETENTION_DAYS + 1)).timestamp() * 1000)
        
        # Insert old ticker directly without triggering cleanup
        with storage._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO ticker (timestamp, symbol, last)
                VALUES (?, ?, ?)
            """, (old_time, "BTCUSDT", 45000.0))
            conn.commit()
        
        # Verify old ticker exists
        all_tickers = storage.query_ticker()
        assert len(all_tickers) == 1
        
        # Insert new ticker (triggers cleanup)
        new_ticker = {
            "timestamp": now,
            "symbol": "BTCUSDT",
            "last": 49500.0
        }
        storage.insert_ticker(new_ticker)
        
        # Old ticker should be deleted
        recent_tickers = storage.query_ticker()
        assert len(recent_tickers) == 1
        assert recent_tickers[0]["timestamp"] == now

    def test_cleanup_old_trades_records(self, storage):
        """Test that old trade records are deleted."""
        now = int(datetime.now().timestamp() * 1000)
        old_time = int((datetime.now() - timedelta(days=RETENTION_DAYS + 1)).timestamp() * 1000)
        
        # Insert old trade directly without triggering cleanup
        with storage._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO trades (id, timestamp, symbol, side, price, amount)
                VALUES (?, ?, ?, ?, ?, ?)
            """, ("old_trade", old_time, "BTCUSDT", "buy", 45000.0, 0.1))
            conn.commit()
        
        # Insert new trades (triggers cleanup)
        new_trades = [
            {
                "id": "new_trade",
                "timestamp": now,
                "symbol": "BTCUSDT",
                "side": "sell",
                "price": 49500.0,
                "amount": 0.1
            }
        ]
        storage.insert_trades(new_trades)
        
        # Only new trade should remain
        results = storage.query_trades()
        assert len(results) == 1
        assert results[0]["id"] == "new_trade"

    def test_cleanup_old_ohlcv_records(self, storage):
        """Test that old OHLCV records are deleted."""
        now = int(datetime.now().timestamp() * 1000)
        old_time = int((datetime.now() - timedelta(days=RETENTION_DAYS + 1)).timestamp() * 1000)
        
        # Insert old candle directly without triggering cleanup
        with storage._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO ohlcv (timestamp, symbol, timeframe, open, high, low, close, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (old_time, "BTCUSDT", "1m", 45000.0, 46000.0, 44000.0, 45500.0, 100.0))
            conn.commit()
        
        # Insert new candles (triggers cleanup)
        new_candles = [[now, 49000.0, 50000.0, 48500.0, 49500.0, 150.0]]
        storage.insert_ohlcv("1m", new_candles)
        
        # Only new candles should remain
        results = storage.query_ohlcv("1m")
        assert len(results) == 1
        assert results[0][0] == now

    def test_cleanup_old_funding_rate_records(self, storage):
        """Test that old funding rate records are deleted."""
        now = int(datetime.now().timestamp() * 1000)
        old_time = int((datetime.now() - timedelta(days=RETENTION_DAYS + 1)).timestamp() * 1000)
        
        # Insert old funding rate directly without triggering cleanup
        with storage._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO funding_rate (timestamp, symbol, funding_rate)
                VALUES (?, ?, ?)
            """, (old_time, "BTCUSDT", 0.0001))
            conn.commit()
        
        # Insert new funding rate (triggers cleanup)
        new_funding = {
            "timestamp": now,
            "symbol": "BTCUSDT",
            "fundingRate": 0.0002
        }
        storage.insert_funding_rate(new_funding)
        
        # Only new funding rate should remain
        results = storage.query_funding_rate()
        assert len(results) == 1
        assert results[0]["timestamp"] == now

    def test_cleanup_old_mark_price_records(self, storage):
        """Test that old mark price records are deleted."""
        now = int(datetime.now().timestamp() * 1000)
        old_time = int((datetime.now() - timedelta(days=RETENTION_DAYS + 1)).timestamp() * 1000)
        
        # Insert old mark price directly without triggering cleanup
        with storage._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO mark_price (timestamp, symbol, mark_price)
                VALUES (?, ?, ?)
            """, (old_time, "BTCUSDT", 45000.0))
            conn.commit()
        
        # Insert new mark price (triggers cleanup)
        new_mark_price = {
            "timestamp": now,
            "symbol": "BTCUSDT",
            "markPrice": 49500.0
        }
        storage.insert_mark_price(new_mark_price)
        
        # Only new mark price should remain
        results = storage.query_mark_price()
        assert len(results) == 1
        assert results[0]["timestamp"] == now

    def test_cleanup_preserves_recent_records(self, storage):
        """Test that recent records are preserved during cleanup."""
        now = int(datetime.now().timestamp() * 1000)
        recent_times = [
            int((datetime.now() - timedelta(days=i)).timestamp() * 1000)
            for i in range(RETENTION_DAYS - 1)
        ]
        
        # Insert multiple recent tickers
        for ts in recent_times:
            ticker = {
                "timestamp": ts,
                "symbol": "BTCUSDT",
                "last": 49000.0
            }
            storage.insert_ticker(ticker)
        
        # Insert new ticker (triggers cleanup)
        new_ticker = {
            "timestamp": now,
            "symbol": "BTCUSDT",
            "last": 49500.0
        }
        storage.insert_ticker(new_ticker)
        
        # All recent records should be preserved
        results = storage.query_ticker()
        assert len(results) == len(recent_times) + 1


class TestPerSymbolIsolation:
    """Test that each symbol gets its own database."""

    def test_different_symbols_different_databases(self, temp_storage_dir):
        """Test that different symbols use different database files."""
        storage_btc = SQLiteStorage(temp_storage_dir, "BTCUSDT")
        storage_eth = SQLiteStorage(temp_storage_dir, "ETHUSDT")
        
        assert storage_btc.db_path != storage_eth.db_path
        assert storage_btc.db_path.exists()
        assert storage_eth.db_path.exists()

    def test_symbol_data_isolation(self, temp_storage_dir):
        """Test that data is isolated between symbols."""
        storage_btc = SQLiteStorage(temp_storage_dir, "BTCUSDT")
        storage_eth = SQLiteStorage(temp_storage_dir, "ETHUSDT")
        
        now = int(datetime.now().timestamp() * 1000)
        
        # Insert ticker for BTC
        btc_ticker = {
            "timestamp": now,
            "symbol": "BTCUSDT",
            "last": 49500.0
        }
        storage_btc.insert_ticker(btc_ticker)
        
        # Insert ticker for ETH
        eth_ticker = {
            "timestamp": now,
            "symbol": "ETHUSDT",
            "last": 3000.0
        }
        storage_eth.insert_ticker(eth_ticker)
        
        # Query each storage
        btc_results = storage_btc.query_ticker()
        eth_results = storage_eth.query_ticker()
        
        assert len(btc_results) == 1
        assert len(eth_results) == 1
        assert btc_results[0]["last"] == 49500.0
        assert eth_results[0]["last"] == 3000.0


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_insert_empty_trades_list(self, storage):
        """Test inserting empty trades list."""
        inserted = storage.insert_trades([])
        assert inserted == 0

    def test_insert_empty_ohlcv_list(self, storage):
        """Test inserting empty OHLCV list."""
        inserted = storage.insert_ohlcv("1m", [])
        assert inserted == 0

    def test_query_nonexistent_timeframe(self, storage):
        """Test querying non-existent timeframe."""
        results = storage.query_ohlcv("1h")
        assert len(results) == 0

    def test_query_with_no_matching_time_range(self, storage):
        """Test querying with time range that has no matches."""
        now = int(datetime.now().timestamp() * 1000)
        
        ticker = {
            "timestamp": now,
            "symbol": "BTCUSDT",
            "last": 49500.0
        }
        storage.insert_ticker(ticker)
        
        # Query for future time range
        results = storage.query_ticker(
            start_time=now + 100000,
            end_time=now + 200000
        )
        
        assert len(results) == 0

    def test_ticker_with_null_fields(self, storage):
        """Test inserting ticker with null/missing fields."""
        now = int(datetime.now().timestamp() * 1000)
        ticker = {
            "timestamp": now,
            "symbol": "BTCUSDT"
            # Most fields are missing
        }
        
        storage.insert_ticker(ticker)
        
        results = storage.query_ticker()
        assert len(results) == 1
        assert results[0]["high"] is None
        assert results[0]["low"] is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
