import pytest

from app import db
from app.market.seed_data import DEFAULT_TICKERS


def test_init_creates_file_in_new_dir():
    assert db.db_path().exists()


def test_seed_cash_and_watchlist():
    assert db.get_cash() == 10000.0
    assert db.get_watchlist() == DEFAULT_TICKERS


def test_init_is_idempotent_and_keeps_changes():
    db.remove_watchlist("AAPL")
    db.set_cash(5.0)
    db.init_db()
    assert "AAPL" not in db.get_watchlist()
    assert db.get_cash() == 5.0


def test_set_cash():
    db.set_cash(1234.5)
    assert db.get_cash() == 1234.5


def test_add_watchlist_uppercases_and_rejects_duplicates():
    assert db.add_watchlist("pypl") is True
    assert db.add_watchlist("PYPL") is False
    assert db.get_watchlist()[-1] == "PYPL"


def test_remove_watchlist():
    assert db.remove_watchlist("tsla") is True
    assert db.remove_watchlist("TSLA") is False
    assert "TSLA" not in db.get_watchlist()


def test_save_position_upsert_and_delete():
    assert db.get_position("AAPL") is None
    db.save_position("aapl", 2, 100.0)
    db.save_position("AAPL", 3, 110.0)
    pos = db.get_position("AAPL")
    assert (pos["ticker"], pos["quantity"], pos["avg_cost"]) == ("AAPL", 3, 110.0)
    assert len(db.get_positions()) == 1
    db.save_position("AAPL", 0, 110.0)
    assert db.get_positions() == []


def test_fractional_position():
    db.save_position("MSFT", 0.25, 400.0)
    assert db.get_position("MSFT")["quantity"] == 0.25


def test_insert_trade_returns_record():
    trade = db.insert_trade("nvda", "buy", 1.5, 120.0)
    assert trade["ticker"] == "NVDA"
    assert trade["side"] == "buy"
    assert trade["quantity"] == 1.5
    assert trade["price"] == 120.0
    assert trade["executed_at"]


def test_snapshots_oldest_first():
    db.insert_snapshot(10000.0)
    db.insert_snapshot(10050.0)
    snaps = db.get_snapshots()
    assert [s["total_value"] for s in snaps] == [10000.0, 10050.0]
    assert set(snaps[0]) == {"total_value", "recorded_at"}


def test_chat_messages_roundtrip_actions():
    db.insert_chat_message("user", "hi")
    db.insert_chat_message("assistant", "done", {"trades": [{"ticker": "AAPL"}]})
    msgs = db.get_chat_messages()
    assert [m["role"] for m in msgs] == ["user", "assistant"]
    assert msgs[0]["actions"] is None
    assert msgs[1]["actions"] == {"trades": [{"ticker": "AAPL"}]}


def test_chat_messages_limit_keeps_latest():
    for i in range(5):
        db.insert_chat_message("user", f"m{i}")
    assert [m["content"] for m in db.get_chat_messages(limit=2)] == ["m3", "m4"]


def test_user_isolation():
    db.add_watchlist("PYPL", user_id="other")
    assert db.get_watchlist(user_id="other") == ["PYPL"]
    assert "PYPL" not in db.get_watchlist()


def test_unique_constraint_enforced():
    import sqlite3

    from app.db.connection import transaction

    with pytest.raises(sqlite3.IntegrityError):
        with transaction() as conn:
            conn.execute("INSERT INTO watchlist (id, ticker, added_at) VALUES ('x', 'AAPL', 'now')")
