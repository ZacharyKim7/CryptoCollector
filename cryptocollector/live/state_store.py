import sqlite3
import time

from cryptocollector import config

_SCHEMA = """
CREATE TABLE IF NOT EXISTS paper_positions (
    symbol TEXT PRIMARY KEY,
    holding INTEGER NOT NULL,
    purchase_price REAL NOT NULL,
    quantity REAL NOT NULL,
    updated_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS paper_trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    price REAL NOT NULL,
    quantity REAL NOT NULL,
    fee REAL NOT NULL,
    timestamp INTEGER NOT NULL
);
"""


class StateStore:
    def __init__(self, db_path: str = config.DB_PATH):
        self.db_path = db_path
        with self._connect() as conn:
            conn.executescript(_SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def load_position(self, symbol: str) -> dict | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT holding, purchase_price, quantity FROM paper_positions WHERE symbol = ?",
                (symbol,),
            ).fetchone()
        if row is None:
            return None
        return {"holding": bool(row[0]), "purchase_price": row[1], "quantity": row[2]}

    def save_position(self, symbol: str, holding: bool, purchase_price: float, quantity: float) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO paper_positions (symbol, holding, purchase_price, quantity, updated_at) "
                "VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT(symbol) DO UPDATE SET holding=excluded.holding, purchase_price=excluded.purchase_price, "
                "quantity=excluded.quantity, updated_at=excluded.updated_at",
                (symbol, int(holding), purchase_price, quantity, int(time.time())),
            )

    def record_trade(self, symbol: str, side: str, price: float, quantity: float, fee: float, timestamp: int) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO paper_trades (symbol, side, price, quantity, fee, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                (symbol, side, price, quantity, fee, timestamp),
            )

    def get_trades(self, symbol: str | None = None) -> list[dict]:
        query = "SELECT symbol, side, price, quantity, fee, timestamp FROM paper_trades"
        params: list = []
        if symbol is not None:
            query += " WHERE symbol = ?"
            params.append(symbol)
        query += " ORDER BY timestamp ASC"

        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()

        return [
            {"symbol": r[0], "side": r[1], "price": r[2], "quantity": r[3], "fee": r[4], "timestamp": r[5]}
            for r in rows
        ]
