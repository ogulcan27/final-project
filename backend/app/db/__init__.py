"""SQLite persistence layer for FinAlly."""

from app.db.connection import db_path, init_db
from app.db.repository import (
    add_watchlist,
    get_cash,
    get_chat_messages,
    get_position,
    get_positions,
    get_snapshots,
    get_watchlist,
    insert_chat_message,
    insert_snapshot,
    insert_trade,
    remove_watchlist,
    save_position,
    set_cash,
)

__all__ = [
    "add_watchlist", "db_path", "get_cash", "get_chat_messages", "get_position", "get_positions",
    "get_snapshots", "get_watchlist", "init_db", "insert_chat_message", "insert_snapshot",
    "insert_trade", "remove_watchlist", "save_position", "set_cash",
]
