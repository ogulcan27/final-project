import asyncio

import pytest

from app import db
from app.market import PriceCache
from app.market.simulator import SimulatorSource
from app.services import WatchlistError, add_ticker, execute_trade, record_snapshots, remove_ticker


@pytest.fixture
def cache():
    db.init_db()
    return PriceCache()


@pytest.fixture
async def source(cache):
    source = SimulatorSource(cache)
    await source.start(db.get_watchlist())
    yield source
    await source.stop()


async def test_add_ticker_updates_db_and_source(source):
    await add_ticker(source, " pypl ")
    assert "PYPL" in db.get_watchlist()
    assert "PYPL" in source.tickers


async def test_add_duplicate_raises(source):
    with pytest.raises(WatchlistError, match="already"):
        await add_ticker(source, "AAPL")


async def test_remove_ticker_updates_db_and_source(source):
    await remove_ticker(source, "nflx")
    assert "NFLX" not in db.get_watchlist()
    assert "NFLX" not in source.tickers


async def test_remove_absent_raises(source):
    with pytest.raises(WatchlistError, match="not in"):
        await remove_ticker(source, "ZZZZ")


async def test_remove_keeps_tracking_held_ticker(source, cache):
    execute_trade(cache, "AAPL", "buy", 1)
    await remove_ticker(source, "AAPL")
    assert "AAPL" not in db.get_watchlist()
    assert "AAPL" in source.tickers


async def test_record_snapshots_runs_periodically():
    db.init_db()
    task = asyncio.create_task(record_snapshots(PriceCache(), interval=0.01))
    await asyncio.sleep(0.05)
    task.cancel()
    assert len(db.get_snapshots()) >= 2
    assert db.get_snapshots()[0]["total_value"] == 10000.0
