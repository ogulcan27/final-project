import asyncio

import httpx

from app.market import PriceCache
from app.market.massive import MassiveSource, parse_snapshot

SAMPLE = {
    "status": "OK",
    "count": 3,
    "tickers": [
        {"ticker": "AAPL", "lastTrade": {"p": 191.23}, "min": {"c": 191.2},
         "day": {"c": 191.0}, "prevDay": {"c": 190.0}},
        {"ticker": "MSFT", "min": {"c": 420.5}, "day": {}, "prevDay": {"c": 418.0}},
        {"ticker": "TSLA", "day": {"c": 0}, "prevDay": {"c": 250.0}},
    ],
}


def make_source(handler, poll_seconds: float = 15.0) -> tuple[PriceCache, MassiveSource]:
    client = httpx.AsyncClient(
        base_url="https://api.massive.com",
        transport=httpx.MockTransport(handler),
        headers={"Authorization": "Bearer k"},
    )
    cache = PriceCache()
    return cache, MassiveSource(cache, "k", poll_seconds=poll_seconds, client=client)


def ok(_: httpx.Request) -> httpx.Response:
    return httpx.Response(200, json=SAMPLE)


def test_parse_fallback_chain():
    assert parse_snapshot(SAMPLE) == {
        "AAPL": (191.23, 190.0),
        "MSFT": (420.5, 418.0),
        "TSLA": (250.0, 250.0),
    }


def test_parse_skips_entries_without_price():
    payload = {"tickers": [{"ticker": "X", "day": {}, "prevDay": {}}]}
    assert parse_snapshot(payload) == {}


def test_parse_handles_null_sections_and_missing_list():
    payload = {"tickers": [{"ticker": "X", "lastTrade": None, "prevDay": {"c": 5.0}}]}
    assert parse_snapshot(payload) == {"X": (5.0, 5.0)}
    assert parse_snapshot({"status": "OK"}) == {}


def test_parse_missing_prev_close_uses_price():
    payload = {"tickers": [{"ticker": "X", "lastTrade": {"p": 10.0}}]}
    assert parse_snapshot(payload) == {"X": (10.0, 10.0)}


async def test_poll_once_writes_cache_and_sends_request_correctly():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        seen["tickers"] = request.url.params["tickers"]
        seen["auth"] = request.headers["authorization"]
        return httpx.Response(200, json=SAMPLE)

    cache, src = make_source(handler)
    src._tickers = {"MSFT", "AAPL", "TSLA"}
    await src.poll_once()
    assert seen == {
        "path": "/v2/snapshot/locale/us/markets/stocks/tickers",
        "tickers": "AAPL,MSFT,TSLA",
        "auth": "Bearer k",
    }
    assert cache.get("AAPL").price == 191.23
    assert cache.get("AAPL").prev_close == 190.0


async def test_poll_ignores_tickers_no_longer_tracked():
    cache, src = make_source(ok)
    src._tickers = {"AAPL"}
    await src.poll_once()
    assert cache.get_price("MSFT") is None


async def test_poll_with_no_tickers_makes_no_request():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json=SAMPLE)

    _, src = make_source(handler)
    await src.poll_once()
    assert calls == []


async def test_http_error_keeps_old_prices():
    cache, src = make_source(lambda r: httpx.Response(429))
    cache.update("AAPL", 100.0)
    src._tickers = {"AAPL"}
    await src.poll_once()
    assert cache.get_price("AAPL") == 100.0


async def test_network_error_keeps_old_prices():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down")

    cache, src = make_source(handler)
    cache.update("AAPL", 100.0)
    src._tickers = {"AAPL"}
    await src.poll_once()
    assert cache.get_price("AAPL") == 100.0


async def test_invalid_json_keeps_old_prices():
    cache, src = make_source(lambda r: httpx.Response(200, content=b"not json"))
    cache.update("AAPL", 100.0)
    src._tickers = {"AAPL"}
    await src.poll_once()
    assert cache.get_price("AAPL") == 100.0


async def test_start_primes_cache_then_polls_in_background():
    count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal count
        count += 1
        return httpx.Response(200, json=SAMPLE)

    cache, src = make_source(handler, poll_seconds=0.01)
    await src.start(["AAPL"])
    assert cache.get_price("AAPL") == 191.23
    await asyncio.sleep(0.1)
    assert count > 2
    await src.stop()


async def test_stop_halts_polling():
    count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal count
        count += 1
        return httpx.Response(200, json=SAMPLE)

    _, src = make_source(handler, poll_seconds=0.01)
    await src.start(["AAPL"])
    await src.stop()
    seen = count
    await asyncio.sleep(0.05)
    assert count == seen


async def test_add_and_remove_ticker():
    cache, src = make_source(ok)
    await src.add_ticker("AAPL")
    await src.add_ticker("AAPL")
    await src.add_ticker("MSFT")
    assert src.tickers == ["AAPL", "MSFT"]
    await src.poll_once()
    await src.remove_ticker("AAPL")
    await src.remove_ticker("AAPL")
    assert src.tickers == ["MSFT"]
    assert "AAPL" not in cache
