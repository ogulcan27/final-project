import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as client:
        yield client


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_fresh_portfolio(client):
    body = client.get("/api/portfolio").json()
    assert body == {"cash_balance": 10000.0, "total_value": 10000.0, "unrealized_pnl": 0.0, "positions": []}


def test_buy_then_sell(client):
    resp = client.post("/api/portfolio/trade", json={"ticker": "aapl", "quantity": 2, "side": "buy"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["trade"]["ticker"] == "AAPL"
    assert body["portfolio"]["positions"][0]["quantity"] == 2
    assert body["portfolio"]["cash_balance"] < 10000.0

    resp = client.post("/api/portfolio/trade", json={"ticker": "AAPL", "quantity": 2, "side": "sell"})
    assert resp.status_code == 200
    assert resp.json()["portfolio"]["positions"] == []


def test_trade_errors_return_400(client):
    resp = client.post("/api/portfolio/trade", json={"ticker": "AAPL", "quantity": 1, "side": "sell"})
    assert resp.status_code == 400
    assert "Insufficient shares" in resp.json()["detail"]
    resp = client.post("/api/portfolio/trade", json={"ticker": "AAPL", "quantity": 1000, "side": "buy"})
    assert resp.status_code == 400


def test_invalid_side_returns_422(client):
    resp = client.post("/api/portfolio/trade", json={"ticker": "AAPL", "quantity": 1, "side": "hold"})
    assert resp.status_code == 422


def test_history_has_startup_and_trade_snapshots(client):
    client.post("/api/portfolio/trade", json={"ticker": "AAPL", "quantity": 1, "side": "buy"})
    history = client.get("/api/portfolio/history").json()
    assert len(history) >= 2
    assert set(history[0]) >= {"total_value", "recorded_at"}


def test_watchlist_default_has_prices(client):
    items = client.get("/api/watchlist").json()
    assert [i["ticker"] for i in items][:2] == ["AAPL", "GOOGL"]
    assert len(items) == 10
    assert set(items[0]) == {"ticker", "price", "previous_price", "change_pct", "direction"}
    assert items[0]["price"] > 0


def test_watchlist_add_and_remove(client):
    resp = client.post("/api/watchlist", json={"ticker": "pypl"})
    assert resp.status_code == 201
    assert resp.json()["ticker"] == "PYPL"
    assert client.post("/api/watchlist", json={"ticker": "PYPL"}).status_code == 409

    assert client.delete("/api/watchlist/PYPL").status_code == 204
    assert client.delete("/api/watchlist/PYPL").status_code == 404
    assert "PYPL" not in [i["ticker"] for i in client.get("/api/watchlist").json()]


def test_startup_tracks_held_tickers_not_on_watchlist():
    with TestClient(app) as client:
        client.post("/api/portfolio/trade", json={"ticker": "AAPL", "quantity": 1, "side": "buy"})
        client.delete("/api/watchlist/AAPL")
    with TestClient(app) as client:
        assert "AAPL" in app.state.market_source.tickers
        assert client.get("/api/portfolio").json()["positions"][0]["ticker"] == "AAPL"


def test_chat_mock(client):
    resp = client.post("/api/chat", json={"message": "hello"})
    assert resp.status_code == 200
    assert "message" in resp.json()
