"""Repository functions for all FinAlly tables."""

import json

from app.db.connection import new_id, now, transaction


def get_cash(user_id: str = "default") -> float:
    """Return the user's cash balance."""
    with transaction() as conn:
        row = conn.execute("SELECT cash_balance FROM users_profile WHERE id = ?", (user_id,)).fetchone()
    return row["cash_balance"]


def set_cash(cash: float, user_id: str = "default") -> None:
    """Set the user's cash balance."""
    with transaction() as conn:
        conn.execute("UPDATE users_profile SET cash_balance = ? WHERE id = ?", (cash, user_id))


def get_watchlist(user_id: str = "default") -> list[str]:
    """Return watched tickers ordered by when they were added."""
    with transaction() as conn:
        rows = conn.execute(
            "SELECT ticker FROM watchlist WHERE user_id = ? ORDER BY added_at, rowid", (user_id,)
        ).fetchall()
    return [r["ticker"] for r in rows]


def add_watchlist(ticker: str, user_id: str = "default") -> bool:
    """Add a ticker; return False if it was already present."""
    with transaction() as conn:
        cur = conn.execute(
            "INSERT OR IGNORE INTO watchlist (id, user_id, ticker, added_at) VALUES (?, ?, ?, ?)",
            (new_id(), user_id, ticker.upper(), now()),
        )
    return cur.rowcount == 1


def remove_watchlist(ticker: str, user_id: str = "default") -> bool:
    """Remove a ticker; return False if it was absent."""
    with transaction() as conn:
        cur = conn.execute(
            "DELETE FROM watchlist WHERE user_id = ? AND ticker = ?", (user_id, ticker.upper())
        )
    return cur.rowcount == 1


def get_positions(user_id: str = "default") -> list[dict]:
    """Return all positions as {ticker, quantity, avg_cost, updated_at}."""
    with transaction() as conn:
        rows = conn.execute(
            "SELECT ticker, quantity, avg_cost, updated_at FROM positions WHERE user_id = ? ORDER BY ticker",
            (user_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_position(ticker: str, user_id: str = "default") -> dict | None:
    """Return one position or None."""
    with transaction() as conn:
        row = conn.execute(
            "SELECT ticker, quantity, avg_cost, updated_at FROM positions WHERE user_id = ? AND ticker = ?",
            (user_id, ticker.upper()),
        ).fetchone()
    return dict(row) if row else None


def save_position(ticker: str, quantity: float, avg_cost: float, user_id: str = "default") -> None:
    """Upsert a position; delete it when quantity is zero."""
    ticker = ticker.upper()
    with transaction() as conn:
        if quantity == 0:
            conn.execute("DELETE FROM positions WHERE user_id = ? AND ticker = ?", (user_id, ticker))
            return
        conn.execute(
            """INSERT INTO positions (id, user_id, ticker, quantity, avg_cost, updated_at)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT (user_id, ticker) DO UPDATE SET
                 quantity = excluded.quantity, avg_cost = excluded.avg_cost, updated_at = excluded.updated_at""",
            (new_id(), user_id, ticker, quantity, avg_cost, now()),
        )


def insert_trade(ticker: str, side: str, quantity: float, price: float, user_id: str = "default") -> dict:
    """Append a trade and return {ticker, side, quantity, price, executed_at}."""
    trade = {"ticker": ticker.upper(), "side": side, "quantity": quantity, "price": price, "executed_at": now()}
    with transaction() as conn:
        conn.execute(
            "INSERT INTO trades (id, user_id, ticker, side, quantity, price, executed_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (new_id(), user_id, *trade.values()),
        )
    return trade


def insert_snapshot(total_value: float, user_id: str = "default") -> None:
    """Record a portfolio value snapshot."""
    with transaction() as conn:
        conn.execute(
            "INSERT INTO portfolio_snapshots (id, user_id, total_value, recorded_at) VALUES (?, ?, ?, ?)",
            (new_id(), user_id, total_value, now()),
        )


def get_snapshots(user_id: str = "default") -> list[dict]:
    """Return snapshots as {total_value, recorded_at}, oldest first."""
    with transaction() as conn:
        rows = conn.execute(
            "SELECT total_value, recorded_at FROM portfolio_snapshots WHERE user_id = ? ORDER BY recorded_at, rowid",
            (user_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def insert_chat_message(role: str, content: str, actions: dict | None = None, user_id: str = "default") -> None:
    """Store a chat message; actions are serialized as JSON."""
    with transaction() as conn:
        conn.execute(
            "INSERT INTO chat_messages (id, user_id, role, content, actions, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (new_id(), user_id, role, content, json.dumps(actions) if actions is not None else None, now()),
        )


def get_chat_messages(limit: int = 20, user_id: str = "default") -> list[dict]:
    """Return the last `limit` messages as {role, content, actions, created_at}, oldest first."""
    with transaction() as conn:
        rows = conn.execute(
            """SELECT role, content, actions, created_at FROM chat_messages WHERE user_id = ?
               ORDER BY created_at DESC, rowid DESC LIMIT ?""",
            (user_id, limit),
        ).fetchall()
    messages = [dict(r) | {"actions": json.loads(r["actions"]) if r["actions"] else None} for r in rows]
    return messages[::-1]
