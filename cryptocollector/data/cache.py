import sqlite3

import pandas as pd

from cryptocollector import config
from cryptocollector.data.coinbase_client import (
    GRANULARITY_SECONDS,
    current_unix_timestamp,
    days_ago_to_unix,
    fetch_candles,
)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS candles (
    symbol TEXT NOT NULL,
    granularity TEXT NOT NULL,
    start_ts INTEGER NOT NULL,
    open REAL,
    high REAL,
    low REAL,
    close REAL,
    volume REAL,
    PRIMARY KEY (symbol, granularity, start_ts)
);
"""


class CandleCache:
    def __init__(self, db_path: str = config.DB_PATH):
        self.db_path = db_path
        with self._connect() as conn:
            conn.execute(_SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def get_latest_timestamp(self, symbol: str, granularity: str) -> int | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT MAX(start_ts) FROM candles WHERE symbol = ? AND granularity = ?",
                (symbol, granularity),
            ).fetchone()
        return row[0] if row and row[0] is not None else None

    def upsert_candles(self, symbol: str, granularity: str, candles: list[dict]) -> int:
        rows = [
            (
                symbol,
                granularity,
                int(c["start"]),
                float(c["open"]),
                float(c["high"]),
                float(c["low"]),
                float(c["close"]),
                float(c["volume"]),
            )
            for c in candles
        ]
        if not rows:
            return 0
        with self._connect() as conn:
            conn.executemany(
                "INSERT OR REPLACE INTO candles "
                "(symbol, granularity, start_ts, open, high, low, close, volume) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                rows,
            )
        return len(rows)

    def fetch_and_update(
        self,
        symbol: str,
        client,
        granularity: str = config.NATIVE_GRANULARITY,
        days_ago_if_empty: int = config.DEFAULT_BACKFILL_DAYS,
    ) -> int:
        """Backfill from scratch if the cache is empty for this symbol,
        otherwise fetch only the gap since the latest cached candle."""
        latest = self.get_latest_timestamp(symbol, granularity)
        now = current_unix_timestamp()
        interval_seconds = GRANULARITY_SECONDS[granularity]

        if latest is None:
            start_ts = days_ago_to_unix(days_ago_if_empty)
        else:
            start_ts = latest + interval_seconds

        if start_ts >= now:
            return 0

        candles = fetch_candles(client, symbol, granularity, start_ts, now)
        return self.upsert_candles(symbol, granularity, candles)

    def get_raw_candles(
        self,
        symbol: str,
        granularity: str = config.NATIVE_GRANULARITY,
        start_ts: int | None = None,
        end_ts: int | None = None,
    ) -> pd.DataFrame:
        query = "SELECT start_ts, open, high, low, close, volume FROM candles WHERE symbol = ? AND granularity = ?"
        params: list = [symbol, granularity]
        if start_ts is not None:
            query += " AND start_ts >= ?"
            params.append(start_ts)
        if end_ts is not None:
            query += " AND start_ts <= ?"
            params.append(end_ts)
        query += " ORDER BY start_ts ASC"

        with self._connect() as conn:
            df = pd.read_sql_query(query, conn, params=params)
        return df

    def get_candles(
        self,
        symbol: str,
        timeframe: str = config.TARGET_TIMEFRAME,
        granularity: str = config.NATIVE_GRANULARITY,
        start_ts: int | None = None,
        end_ts: int | None = None,
    ) -> pd.DataFrame:
        """Return OHLCV candles resampled to `timeframe` (a pandas offset
        alias, e.g. "4h"). Coinbase has no native 4-hour granularity, so we
        cache the native (finer) granularity and aggregate it here instead."""
        df = self.get_raw_candles(symbol, granularity, start_ts, end_ts)
        if df.empty:
            return df

        df["timestamp"] = pd.to_datetime(df["start_ts"], unit="s", utc=True)
        df = df.set_index("timestamp").sort_index()

        resampled = df.resample(timeframe).agg(
            {
                "open": "first",
                "high": "max",
                "low": "min",
                "close": "last",
                "volume": "sum",
            }
        )
        resampled = resampled.dropna(subset=["open", "high", "low", "close"])
        resampled["start_ts"] = (resampled.index.view("int64") // 10**9).astype(int)
        return resampled.reset_index(drop=True)
