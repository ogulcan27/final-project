import json

from fastapi import FastAPI
from starlette.requests import Request

from app.market import PriceCache
from app.market.stream import price_events, stream_prices


def disconnect_after(n: int):
    """Return an is_disconnected callable that reports True after n calls."""
    calls = 0

    async def is_disconnected() -> bool:
        nonlocal calls
        calls += 1
        return calls > n

    return is_disconnected


def parse(message: str) -> dict:
    assert message.startswith("data: ") and message.endswith("\n\n")
    return json.loads(message[len("data: "):])


async def collect(cache: PriceCache, cycles: int) -> list[str]:
    gen = price_events(cache, disconnect_after(cycles), interval=0)
    return [m async for m in gen]


async def test_first_message_sets_retry():
    messages = await collect(PriceCache(), 1)
    assert messages == ["retry: 1000\n\n"]


async def test_initial_push_sends_every_ticker():
    cache = PriceCache()
    cache.update("AAPL", 190.0, prev_close=189.0)
    cache.update("MSFT", 420.0)
    messages = await collect(cache, 1)
    events = [parse(m) for m in messages[1:]]
    assert {e["ticker"] for e in events} == {"AAPL", "MSFT"}
    aapl = next(e for e in events if e["ticker"] == "AAPL")
    assert aapl["price"] == 190.0 and aapl["prev_close"] == 189.0


async def test_unchanged_tickers_are_not_resent():
    cache = PriceCache()
    cache.update("AAPL", 190.0)
    messages = await collect(cache, 3)
    assert len(messages) == 2  # retry + one data event


async def test_changed_ticker_is_resent_with_direction():
    cache = PriceCache()
    cache.update("AAPL", 190.0)
    gen = price_events(cache, disconnect_after(3), interval=0)
    seen = [await anext(gen), await anext(gen)]  # retry, first data
    cache.update("AAPL", 191.0)
    seen += [m async for m in gen]
    last = parse(seen[-1])
    assert last["price"] == 191.0 and last["direction"] == "up"


async def test_ticker_added_later_is_pushed():
    cache = PriceCache()
    gen = price_events(cache, disconnect_after(3), interval=0)
    first = await anext(gen)
    cache.update("NEW", 10.0)
    rest = [m async for m in gen]
    assert first == "retry: 1000\n\n"
    assert parse(rest[0])["ticker"] == "NEW"


async def test_route_returns_sse_response():
    app = FastAPI()
    app.state.price_cache = PriceCache()
    scope = {"type": "http", "app": app, "headers": [], "method": "GET", "path": "/"}
    response = await stream_prices(Request(scope))
    assert response.media_type == "text/event-stream"
    assert response.headers["cache-control"] == "no-cache"
    assert response.headers["x-accel-buffering"] == "no"
