import pytest

from app.market import MarketDataSource, PriceCache, PriceUpdate


def test_first_update_has_flat_direction():
    u = PriceCache().update("AAPL", 100.0)
    assert (u.previous_price, u.prev_close, u.direction) == (100.0, 100.0, "flat")


def test_previous_price_and_direction_up():
    cache = PriceCache()
    cache.update("AAPL", 100.0, prev_close=99.0)
    u = cache.update("AAPL", 101.0)
    assert (u.previous_price, u.prev_close, u.direction) == (100.0, 99.0, "up")
    assert u.change_pct == round(2 / 99 * 100, 3)


def test_direction_down():
    cache = PriceCache()
    cache.update("AAPL", 100.0)
    assert cache.update("AAPL", 99.0).direction == "down"


def test_prev_close_can_be_overwritten():
    cache = PriceCache()
    cache.update("AAPL", 100.0, prev_close=99.0)
    assert cache.update("AAPL", 100.0, prev_close=98.0).prev_close == 98.0


def test_change_pct_zero_prev_close():
    u = PriceUpdate("X", 5.0, 5.0, 0.0, 0.0)
    assert u.change_pct == 0.0


def test_get_and_get_price():
    cache = PriceCache()
    assert cache.get("AAPL") is None
    assert cache.get_price("AAPL") is None
    cache.update("AAPL", 100.0)
    assert cache.get_price("AAPL") == 100.0
    assert cache.get("AAPL").ticker == "AAPL"


def test_all_and_contains():
    cache = PriceCache()
    cache.update("AAPL", 1.0)
    cache.update("MSFT", 2.0)
    assert {u.ticker for u in cache.all()} == {"AAPL", "MSFT"}
    assert "AAPL" in cache and "TSLA" not in cache


def test_remove_is_idempotent():
    cache = PriceCache()
    cache.update("AAPL", 100.0)
    cache.remove("AAPL")
    cache.remove("AAPL")
    assert cache.get_price("AAPL") is None


def test_to_dict_shape():
    d = PriceCache().update("AAPL", 100.0).to_dict()
    assert set(d) == {
        "ticker", "price", "previous_price", "prev_close",
        "change_pct", "direction", "timestamp",
    }


def test_interface_is_abstract():
    with pytest.raises(TypeError):
        MarketDataSource()
