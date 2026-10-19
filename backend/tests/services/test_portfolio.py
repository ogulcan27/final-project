import pytest

from app import db
from app.market import PriceCache
from app.services import TradeError, execute_trade, get_portfolio


@pytest.fixture
def cache():
    db.init_db()
    cache = PriceCache()
    cache.update("AAPL", 100.0)
    return cache


def test_buy_updates_cash_position_trade_and_snapshot(cache):
    trade = execute_trade(cache, "aapl", "buy", 10)
    assert trade["ticker"] == "AAPL"
    assert trade["price"] == 100.0
    assert db.get_cash() == 9000.0
    assert db.get_position("AAPL")["quantity"] == 10
    assert len(db.get_snapshots()) == 1


def test_buy_averages_cost(cache):
    execute_trade(cache, "AAPL", "buy", 10)
    cache.update("AAPL", 200.0)
    execute_trade(cache, "AAPL", "buy", 10)
    assert db.get_position("AAPL")["avg_cost"] == 150.0


def test_sell_all_removes_position(cache):
    execute_trade(cache, "AAPL", "buy", 5)
    cache.update("AAPL", 110.0)
    execute_trade(cache, "AAPL", "sell", 5)
    assert db.get_position("AAPL") is None
    assert db.get_cash() == 10050.0


def test_partial_sell_at_loss_keeps_avg_cost(cache):
    execute_trade(cache, "AAPL", "buy", 4)
    cache.update("AAPL", 90.0)
    execute_trade(cache, "AAPL", "sell", 1.5)
    position = db.get_position("AAPL")
    assert position["quantity"] == 2.5
    assert position["avg_cost"] == 100.0
    assert db.get_cash() == 10000 - 400 + 135


@pytest.mark.parametrize(
    ("ticker", "side", "quantity", "message"),
    [
        ("AAPL", "buy", 1000, "Insufficient cash"),
        ("AAPL", "sell", 1, "Insufficient shares"),
        ("AAPL", "buy", 0, "Quantity must be positive"),
        ("ZZZZ", "buy", 1, "No price available"),
        ("AAPL", "hold", 1, "Invalid side"),
    ],
)
def test_rejected_trades_change_nothing(cache, ticker, side, quantity, message):
    with pytest.raises(TradeError, match=message):
        execute_trade(cache, ticker, side, quantity)
    assert db.get_cash() == 10000.0
    assert db.get_positions() == []


def test_get_portfolio_values_positions(cache):
    execute_trade(cache, "AAPL", "buy", 10)
    cache.update("AAPL", 120.0)
    portfolio = get_portfolio(cache)
    assert portfolio["cash_balance"] == 9000.0
    assert portfolio["total_value"] == 10200.0
    assert portfolio["unrealized_pnl"] == 200.0
    assert portfolio["positions"] == [
        {
            "ticker": "AAPL",
            "quantity": 10,
            "avg_cost": 100.0,
            "current_price": 120.0,
            "market_value": 1200.0,
            "unrealized_pnl": 200.0,
            "pnl_pct": 20.0,
        }
    ]
