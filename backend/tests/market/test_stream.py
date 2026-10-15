import asyncio
import json

import httpx
import pytest
import uvicorn
from fastapi import FastAPI

from app.market import PriceCache
from app.market import cache as cache_module
from app.market.stream import price_events, router


async def take(gen, n: int) -> list:
    return [await anext(gen) for _ in range(n)]


async def test_first_event_sets_retry():
    gen = price_events(PriceCache(), interval=0)
    assert (await anext(gen)).retry == 1000


async def test_initial_push_sends_every_ticker():
    cache = PriceCache()
    cache.update("AAPL", 190.0, prev_close=189.0)
    cache.update("MSFT", 420.0)
    events = await take(price_events(cache, interval=0), 3)
    data = {e.data["ticker"]: e.data for e in events[1:]}
    assert set(data) == {"AAPL", "MSFT"}
    assert data["AAPL"]["price"] == 190.0 and data["AAPL"]["prev_close"] == 189.0


async def test_unchanged_tickers_are_not_resent():
    cache = PriceCache()
    cache.update("AAPL", 190.0)
    gen = price_events(cache, interval=0)
    await take(gen, 2)
    with pytest.raises(TimeoutError):
        await asyncio.wait_for(anext(gen), 0.05)


async def test_changed_ticker_is_resent_with_direction():
    cache = PriceCache()
    cache.update("AAPL", 190.0)
    gen = price_events(cache, interval=0)
    await take(gen, 2)
    cache.update("AAPL", 191.0)
    event = await anext(gen)
    assert event.data["price"] == 191.0 and event.data["direction"] == "up"


async def test_update_with_same_timestamp_is_still_sent(monkeypatch):
    monkeypatch.setattr(cache_module.time, "time", lambda: 1.0)
    cache = PriceCache()
    cache.update("AAPL", 190.0)
    gen = price_events(cache, interval=0)
    await take(gen, 2)
    cache.update("AAPL", 191.0)
    assert (await asyncio.wait_for(anext(gen), 1)).data["price"] == 191.0


async def test_ticker_added_later_is_pushed():
    cache = PriceCache()
    gen = price_events(cache, interval=0)
    await anext(gen)
    cache.update("NEW", 10.0)
    assert (await anext(gen)).data["ticker"] == "NEW"


@pytest.fixture
async def server():
    """Serve the stream router over real HTTP on a free port."""
    app = FastAPI()
    app.state.price_cache = PriceCache()
    app.include_router(router)
    srv = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=0, log_level="warning"))
    task = asyncio.create_task(srv.serve())
    while not srv.started:
        await asyncio.sleep(0.01)
    port = srv.servers[0].sockets[0].getsockname()[1]
    yield app, f"http://127.0.0.1:{port}"
    srv.should_exit = True
    await asyncio.wait_for(task, 5)


async def data_lines(resp: httpx.Response):
    async for line in resp.aiter_lines():
        if line:
            yield line


def parse(line: str) -> dict:
    assert line.startswith("data: ")
    return json.loads(line[len("data: "):])


async def test_stream_over_http(server):
    app, url = server
    app.state.price_cache.update("AAPL", 190.0, prev_close=189.0)
    async with httpx.AsyncClient(base_url=url) as client:
        async with client.stream("GET", "/api/stream/prices") as resp:
            assert resp.headers["content-type"].startswith("text/event-stream")
            assert resp.headers["cache-control"] == "no-cache"
            assert resp.headers["x-accel-buffering"] == "no"
            lines = data_lines(resp)
            assert await anext(lines) == "retry: 1000"
            first = parse(await anext(lines))
            assert (first["ticker"], first["price"], first["prev_close"]) == ("AAPL", 190.0, 189.0)
            app.state.price_cache.update("AAPL", 191.0)
            assert parse(await anext(lines))["direction"] == "up"


async def test_idle_stream_sends_keepalive_ping(server, monkeypatch):
    monkeypatch.setattr("fastapi.routing._PING_INTERVAL", 0.05)
    _, url = server
    async with httpx.AsyncClient(base_url=url) as client:
        async with client.stream("GET", "/api/stream/prices") as resp:
            lines = data_lines(resp)
            assert await anext(lines) == "retry: 1000"
            assert await asyncio.wait_for(anext(lines), 2) == ": ping"
