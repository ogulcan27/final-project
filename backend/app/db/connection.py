"""SQLite connection handling and lazy initialization."""

import os
import sqlite3
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from app.market.seed_data import DEFAULT_TICKERS

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SCHEMA_PATH = Path(__file__).with_name("schema.sql")
DEFAULT_CASH = 10000.0


def db_path() -> Path:
    """Return the DB file path from FINALLY_DB_PATH or the project default."""
    return Path(os.environ.get("FINALLY_DB_PATH", PROJECT_ROOT / "db" / "finally.db"))


def connect() -> sqlite3.Connection:
    """Open a connection with dict-like rows, creating the parent directory."""
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def transaction() -> Iterator[sqlite3.Connection]:
    """Yield a connection that commits on success and always closes."""
    conn = connect()
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def now() -> str:
    """Current time as an ISO-8601 UTC string."""
    return datetime.now(UTC).isoformat()


def new_id() -> str:
    """New UUID string for a primary key."""
    return str(uuid.uuid4())


def init_db() -> None:
    """Create tables and seed the default user and watchlist if missing."""
    with transaction() as conn:
        conn.executescript(SCHEMA_PATH.read_text())
        created = conn.execute(
            "INSERT OR IGNORE INTO users_profile (id, cash_balance, created_at) VALUES (?, ?, ?)",
            ("default", DEFAULT_CASH, now()),
        ).rowcount
        if created:
            conn.executemany(
                "INSERT INTO watchlist (id, user_id, ticker, added_at) VALUES (?, 'default', ?, ?)",
                [(new_id(), t, now()) for t in DEFAULT_TICKERS],
            )
