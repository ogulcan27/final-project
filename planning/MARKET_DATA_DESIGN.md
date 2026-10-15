# Market Data Backend - Detailed Design

Implementation guide for the market data layer of FinAlly: one abstract interface, two interchangeable sources (simulator, Massive REST), a shared in-memory price cache, and the SSE stream. Contract with the rest of the system is in `PLAN.md` (sections 5, 6, 8).

## 1. Overview

```
            +--------------------+        +--------------------+
            |  SimulatorSource   |        |   MassiveSource    |
            |  (GBM, 500ms)      |        |  (REST poll, 15s)  |
            +---------+----------+        +----------+---------+
                      |   implements MarketDataSource |
                      +---------------+---------------+
                                      | writes
                                      v
                              +---------------+
                              |  PriceCache   |  latest + previous price per ticker
                              +-------+-------+
                    reads             |             reads
        +-----------------+-----------+-----------+------------------+
        | GET /api/stream/prices (SSE)  | trade execution | watchlist / portfolio / chat context |
        +--------------------------------+-----------------+--------------------------------------+
```

Design rules:

- Sources only **write** to the cache. Everything else only **reads** from it. Downstream code never knows which source is active.
- Everything runs on the single asyncio event loop, so the cache needs no locks.
- The active source is chosen once at startup from `MASSIVE_API_KEY`.
- The source owns the set of tracked tickers. Watchlist add/remove calls `add_ticker` / `remove_ticker`.

## 2. Module Layout

```
backend/
  pyproject.toml
  app/
    main.py                  # FastAPI app + lifespan wiring
    market/
      __init__.py            # re-exports: PriceCache, PriceUpdate, create_market_source
      models.py              # PriceUpdate
      cache.py               # PriceCache
      interface.py           # MarketDataSource (ABC)
      seed_data.py           # seed prices, GBM params, sector groups
      simulator.py           # SimulatorSource
      massive.py             # MassiveSource
      factory.py             # create_market_source()
      stream.py              # SSE router
  tests/market/
```

Dependencies:

```bash
cd backend
uv add fastapi uvicorn httpx
uv add --dev pytest pytest-asyncio
```

`httpx` is used directly against the Massive REST API (no extra SDK, async-native, trivial to mock in tests).

## 3. Data Model

`app/market/models.py`

```python
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PriceUpdate:
    """Latest price snapshot for one ticker.

    previous_price is the price before this update (drives the green/red flash).
    prev_close is the prior session close (drives daily change %).
    timestamp is unix seconds, set by the backend when the cache is written.
    """

    ticker: str
    price: float
    previous_price: float
    prev_close: float
    timestamp: float

    @property
    def direction(self) -> str:
        if self.price > self.previous_price:
            return "up"
        if self.price < self.previous_price:
            return "down"
        return "flat"

    @property
    def change_pct(self) -> float:
        """Percent change versus the previous session close."""
        if self.prev_close == 0:
            return 0.0
        return round((self.price - self.prev_close) / self.prev_close * 100, 3)

    def to_dict(self) -> dict:
        return {
            "ticker": self.ticker,
            "price": self.price,
            "previous_price": self.previous_price,
            "prev_close": self.prev_close,
            "change_pct": self.change_pct,
            "direction": self.direction,
            "timestamp": self.timestamp,
        }
```

SSE payload example (one event per ticker):

```
data: {"ticker":"AAPL","price":190.42,"previous_price":190.38,"prev_close":190.0,"change_pct":0.221,"direction":"up","timestamp":1760000000.5}
```

## 4. Price Cache

`app/market/cache.py`

```python
import time

from .models import PriceUpdate


class PriceCache:
    """In-memory latest price per ticker. Single event loop, so no locking."""

    def __init__(self) -> None:
        self._prices: dict[str, PriceUpdate] = {}

    def update(
        self, ticker: str, price: float, prev_close: float | None = None
    ) -> PriceUpdate:
        """Store a new price. Keeps the old price as previous_price.

        prev_close defaults to the value already cached, or to price on first sight.
        """
        old = self._prices.get(ticker)
        update = PriceUpdate(
            ticker=ticker,
            price=price,
            previous_price=old.price if old else price,
            prev_close=prev_close if prev_close is not None
            else (old.prev_close if old else price),
            timestamp=time.time(),
        )
        self._prices[ticker] = update
        return update

    def get(self, ticker: str) -> PriceUpdate | None:
        return self._prices.get(ticker)

    def get_price(self, ticker: str) -> float | None:
        update = self._prices.get(ticker)
        return update.price if update else None

    def all(self) -> list[PriceUpdate]:
        return list(self._prices.values())

    def remove(self, ticker: str) -> None:
        self._prices.pop(ticker, None)

    def __contains__(self, ticker: str) -> bool:
        return ticker in self._prices
```

## 5. Unified Interface

`app/market/interface.py`

```python
from abc import ABC, abstractmethod


class MarketDataSource(ABC):
    """A background producer that keeps a PriceCache fresh.

    Implementations receive the cache in their constructor and write to it.
    """

    @abstractmethod
    async def start(self, tickers: list[str]) -> None:
        """Begin producing prices for the given tickers (spawns a background task)."""

    @abstractmethod
    async def stop(self) -> None:
        """Cancel the background task and release resources."""

    @abstractmethod
    async def add_ticker(self, ticker: str) -> None:
        """Start tracking a ticker. Idempotent."""

    @abstractmethod
    async def remove_ticker(self, ticker: str) -> None:
        """Stop tracking a ticker and drop it from the cache. Idempotent."""

    @property
    @abstractmethod
    def tickers(self) -> list[str]:
        """Currently tracked tickers."""
```

Contract notes:

- Tickers are normalized to upper case by the API layer before reaching the source.
- After `start()` returns, the simulator has already seeded the cache; Massive may take up to one poll to produce the first prices (see 7.4).
- `remove_ticker` removes the cache entry, so a ticker with an open position that is removed from the watchlist must stay tracked. The watchlist route handles this (section 9).

## 6. Simulator

### 6.1 Seed data

`app/market/seed_data.py`

```python
SEED_PRICES: dict[str, float] = {
    "AAPL": 190.0, "GOOGL": 175.0, "MSFT": 420.0, "AMZN": 185.0, "TSLA": 250.0,
    "NVDA": 120.0, "META": 500.0, "JPM": 200.0, "V": 275.0, "NFLX": 650.0,
}

# (annual drift mu, annual volatility sigma)
GBM_PARAMS: dict[str, tuple[float, float]] = {
    "AAPL": (0.08, 0.25), "GOOGL": (0.08, 0.28), "MSFT": (0.09, 0.24),
    "AMZN": (0.09, 0.30), "TSLA": (0.05, 0.55), "NVDA": (0.15, 0.50),
    "META": (0.10, 0.35), "JPM": (0.06, 0.22), "V": (0.07, 0.20),
    "NFLX": (0.08, 0.38),
}
DEFAULT_PARAMS = (0.05, 0.30)

SECTORS: dict[str, str] = {
    "AAPL": "tech", "GOOGL": "tech", "MSFT": "tech", "AMZN": "tech",
    "TSLA": "tech", "NVDA": "tech", "META": "tech", "NFLX": "tech",
    "JPM": "finance", "V": "finance",
}
```

### 6.2 Math

Each tick, per ticker (geometric Brownian motion, exact discretization):

```
S_next = S * exp((mu - sigma^2 / 2) * dt + sigma * sqrt(dt) * z)
```

- `dt` is in years. A real 0.5s tick is ~8.5e-8 years, which moves prices by ~0.01% - invisible. The simulator multiplies `dt` by `TIME_SPEEDUP = 30` so a 0.3 vol stock has a per-tick std of ~0.05% (sensible for a demo). This is a tunable constant, not a statistical claim.
- **Correlation** without a matrix library: each shock is a mix of a market factor, a sector factor and noise:
  `z_i = sqrt(a) * Z_market + sqrt(b) * Z_sector + sqrt(1 - a - b) * eps_i`
  with `a = 0.3`, `b = 0.3` for known sectors (`b = 0` for unknown tickers). Same-sector correlation = 0.6, cross-sector = 0.3. Variance of `z_i` is exactly 1.
- **Events**: each tick each ticker has `EVENT_PROB = 0.0005` of a sudden 2-5% jump (random sign). With 10 tickers at 2 ticks/s that is roughly one event every 100 seconds.
- Unknown tickers (user-added) get a random seed price in `[50, 300]` and `DEFAULT_PARAMS`.
- The session `prev_close` is the seed price, fixed at seed time, so "daily change %" is the move since app start.

### 6.3 Implementation

`app/market/simulator.py`

```python
import asyncio
import contextlib
import math
import random

from .cache import PriceCache
from .interface import MarketDataSource
from .seed_data import DEFAULT_PARAMS, GBM_PARAMS, SECTORS, SEED_PRICES

TICK_SECONDS = 0.5
TRADING_SECONDS_PER_YEAR = 252 * 6.5 * 3600
TIME_SPEEDUP = 30
DT = TICK_SECONDS / TRADING_SECONDS_PER_YEAR * TIME_SPEEDUP

MARKET_WEIGHT = 0.3
SECTOR_WEIGHT = 0.3
EVENT_PROB = 0.0005


class SimulatorSource(MarketDataSource):
    """GBM price simulator with correlated moves and occasional jump events."""

    def __init__(self, cache: PriceCache, rng: random.Random | None = None) -> None:
        self.cache = cache
        self.rng = rng or random.Random()
        self._prices: dict[str, float] = {}  # unrounded internal state
        self._task: asyncio.Task | None = None

    @property
    def tickers(self) -> list[str]:
        return list(self._prices)

    async def start(self, tickers: list[str]) -> None:
        for ticker in tickers:
            self._seed(ticker)
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None

    async def add_ticker(self, ticker: str) -> None:
        if ticker not in self._prices:
            self._seed(ticker)

    async def remove_ticker(self, ticker: str) -> None:
        self._prices.pop(ticker, None)
        self.cache.remove(ticker)

    def _seed(self, ticker: str) -> None:
        price = SEED_PRICES.get(ticker) or round(self.rng.uniform(50, 300), 2)
        self._prices[ticker] = price
        self.cache.update(ticker, price, prev_close=price)

    async def _run(self) -> None:
        while True:
            self.step()
            await asyncio.sleep(TICK_SECONDS)

    def step(self) -> None:
        """Advance every ticker by one tick and write to the cache."""
        market_z = self.rng.gauss(0, 1)
        sector_z: dict[str, float] = {}
        for ticker, price in self._prices.items():
            mu, sigma = GBM_PARAMS.get(ticker, DEFAULT_PARAMS)
            z = self._correlated_shock(ticker, market_z, sector_z)
            price *= math.exp((mu - 0.5 * sigma**2) * DT + sigma * math.sqrt(DT) * z)
            if self.rng.random() < EVENT_PROB:
                price *= 1 + self.rng.choice([-1, 1]) * self.rng.uniform(0.02, 0.05)
            self._prices[ticker] = price
            self.cache.update(ticker, round(price, 2))

    def _correlated_shock(
        self, ticker: str, market_z: float, sector_z: dict[str, float]
    ) -> float:
        sector = SECTORS.get(ticker)
        b = SECTOR_WEIGHT if sector else 0.0
        if sector and sector not in sector_z:
            sector_z[sector] = self.rng.gauss(0, 1)
        z_sector = sector_z.get(sector, 0.0)
        noise = self.rng.gauss(0, 1)
        return (
            math.sqrt(MARKET_WEIGHT) * market_z
            + math.sqrt(b) * z_sector
            + math.sqrt(1 - MARKET_WEIGHT - b) * noise
        )
```

`step()` is synchronous and public so tests can drive it deterministically with a seeded `random.Random` and no sleeping. Prices cannot go negative (multiplicative `exp`).

## 7. Massive API Source

Massive (formerly Polygon.io) is polled over REST. Free tier = 5 calls/min, so **one call per poll** for the whole ticker set using the full-market snapshot endpoint with a `tickers` filter.

### 7.1 Endpoint

```
GET https://api.massive.com/v2/snapshot/locale/us/markets/stocks/tickers?tickers=AAPL,MSFT,TSLA
Authorization: Bearer <MASSIVE_API_KEY>
```

(The key may alternatively be sent as an `apiKey` query parameter. Tickers are case-sensitive, upper case.)

Abbreviated response (fields we use are marked):

```json
{
  "status": "OK",
  "count": 2,
  "tickers": [
    {
      "ticker": "AAPL",                                  // used
      "todaysChange": 1.23,
      "todaysChangePerc": 0.65,
      "updated": 1760000000000000000,
      "lastTrade": {"p": 191.23, "s": 100, "t": 1760000000000000000},   // p used
      "min":      {"c": 191.20, "o": 191.0, "h": 191.3, "l": 190.9, "v": 1200},  // c is fallback
      "day":      {"c": 191.23, "o": 190.1, "h": 192.0, "l": 189.8, "v": 5000000},
      "prevDay":  {"c": 190.00, "o": 189.0, "h": 191.0, "l": 188.5, "v": 4800000}  // c used
    }
  ]
}
```

Notes:

- `lastTrade` is only present if the plan includes trades; `lastQuote` likewise. The parser therefore falls back: `lastTrade.p` -> `min.c` -> `day.c` -> `prevDay.c`.
- Tickers unknown to Massive are simply absent from `tickers`. They never get a price.
- Timestamps in the payload are nanoseconds and plan-dependent; the cache stamps its own `time.time()` instead.
- Outside market hours `day` may be empty/zeroed; the fallback chain skips zero/missing values.

### 7.2 Implementation

`app/market/massive.py`

```python
import asyncio
import contextlib
import logging

import httpx

from .cache import PriceCache
from .interface import MarketDataSource

log = logging.getLogger(__name__)

BASE_URL = "https://api.massive.com"
SNAPSHOT_PATH = "/v2/snapshot/locale/us/markets/stocks/tickers"


def parse_snapshot(payload: dict) -> dict[str, tuple[float, float]]:
    """Map a snapshot response to {ticker: (price, prev_close)}.

    Entries with no usable price are skipped.
    """
    result: dict[str, tuple[float, float]] = {}
    for item in payload.get("tickers", []):
        prev_close = (item.get("prevDay") or {}).get("c") or 0.0
        candidates = [
            (item.get("lastTrade") or {}).get("p"),
            (item.get("min") or {}).get("c"),
            (item.get("day") or {}).get("c"),
            prev_close,
        ]
        price = next((p for p in candidates if p), None)
        if price:
            result[item["ticker"]] = (float(price), float(prev_close or price))
    return result


class MassiveSource(MarketDataSource):
    """Polls the Massive REST snapshot endpoint for the union of tracked tickers."""

    def __init__(
        self,
        cache: PriceCache,
        api_key: str,
        poll_seconds: float = 15.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.cache = cache
        self.poll_seconds = poll_seconds
        self._tickers: set[str] = set()
        self._task: asyncio.Task | None = None
        self._client = client or httpx.AsyncClient(
            base_url=BASE_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10.0,
        )

    @property
    def tickers(self) -> list[str]:
        return sorted(self._tickers)

    async def start(self, tickers: list[str]) -> None:
        self._tickers = set(tickers)
        await self.poll_once()  # prime the cache so the first SSE push has data
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None
        await self._client.aclose()

    async def add_ticker(self, ticker: str) -> None:
        self._tickers.add(ticker)

    async def remove_ticker(self, ticker: str) -> None:
        self._tickers.discard(ticker)
        self.cache.remove(ticker)

    async def _run(self) -> None:
        while True:
            await asyncio.sleep(self.poll_seconds)
            await self.poll_once()

    async def poll_once(self) -> None:
        """One snapshot request for all tracked tickers; failures are logged, not raised."""
        if not self._tickers:
            return
        try:
            resp = await self._client.get(
                SNAPSHOT_PATH, params={"tickers": ",".join(sorted(self._tickers))}
            )
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            log.warning("Massive poll failed: %s", exc)
            return
        for ticker, (price, prev_close) in parse_snapshot(resp.json()).items():
            self.cache.update(ticker, price, prev_close=prev_close)
```

### 7.3 Polling interval

Env var `MASSIVE_POLL_SECONDS` (default `15`, matching the free tier's 5 calls/min with headroom). Paid tiers can lower it to 2-5. Because there is one request per poll regardless of ticker count, the watchlist size does not affect rate limits. Snapshot URLs get long beyond a few hundred tickers; not a concern for this app.

### 7.4 Behavior to be aware of

- A newly added ticker has no price until the next poll (up to 15s). Trade and watchlist code must handle `cache.get_price(t) is None` (return HTTP 400 "price not available yet", do not crash).
- On HTTP 429 or network errors the previous prices stay in the cache and the next poll retries. Prices go stale but the app keeps working. SSE sends only when a cache timestamp changes, so stale tickers are not re-pushed.
- Between polls prices are flat, so the UI flashes every ~15s instead of every 500ms. That is expected for REST polling.
- A ticker added with an invalid symbol appears in the watchlist with no price. The watchlist route should reject a symbol that has no price after the first poll (optional validation, see section 9).

## 8. Factory and Lifecycle

`app/market/factory.py`

```python
import os

from .cache import PriceCache
from .interface import MarketDataSource
from .massive import MassiveSource
from .simulator import SimulatorSource


def create_market_source(cache: PriceCache) -> MarketDataSource:
    """Massive if MASSIVE_API_KEY is set and non-empty, else the simulator."""
    api_key = os.getenv("MASSIVE_API_KEY", "").strip()
    if api_key:
        poll = float(os.getenv("MASSIVE_POLL_SECONDS", "15"))
        return MassiveSource(cache, api_key, poll_seconds=poll)
    return SimulatorSource(cache)
```

`app/market/__init__.py`

```python
from .cache import PriceCache
from .factory import create_market_source
from .interface import MarketDataSource
from .models import PriceUpdate

__all__ = ["MarketDataSource", "PriceCache", "PriceUpdate", "create_market_source"]
```

`app/main.py` (market-data parts only)

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.market import PriceCache, create_market_source
from app.market.stream import router as stream_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    cache = PriceCache()
    source = create_market_source(cache)
    tickers = load_tracked_tickers()  # watchlist UNION open positions, from SQLite
    await source.start(tickers)
    app.state.price_cache = cache
    app.state.market_source = source
    yield
    await source.stop()


app = FastAPI(lifespan=lifespan)
app.include_router(stream_router)
```

`load_tracked_tickers()` returns the union of watchlist tickers and tickers with open positions, so held positions always have a price.

## 9. Integration with the Rest of the Backend

Reading prices (trades, portfolio, chat context):

```python
def require_price(request: Request, ticker: str) -> float:
    price = request.app.state.price_cache.get_price(ticker)
    if price is None:
        raise HTTPException(400, f"No price available for {ticker}")
    return price
```

Watchlist routes keep the source in sync:

```python
@router.post("/api/watchlist")
async def add_watchlist(body: TickerBody, request: Request):
    ticker = body.ticker.upper()
    await request.app.state.market_source.add_ticker(ticker)
    db_add_watchlist(ticker)
    return {"ticker": ticker}


@router.delete("/api/watchlist/{ticker}")
async def remove_watchlist(ticker: str, request: Request):
    ticker = ticker.upper()
    db_remove_watchlist(ticker)
    if not db_has_position(ticker):  # keep pricing held positions
        await request.app.state.market_source.remove_ticker(ticker)
    return {"ticker": ticker}
```

`GET /api/watchlist` joins DB tickers with `cache.get(ticker).to_dict()` (price, change_pct, direction). The chat flow's `watchlist_changes` and `trades` use the same helpers as the REST routes, so source sync is identical for manual and AI-driven changes.

## 10. SSE Endpoint

`app/market/stream.py`

```python
import asyncio
import json

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/api/stream")

PUSH_SECONDS = 0.5


@router.get("/prices")
async def stream_prices(request: Request) -> StreamingResponse:
    """Long-lived SSE stream: one event per ticker whose price changed since last push."""
    cache = request.app.state.price_cache

    async def events():
        yield "retry: 1000\n\n"  # EventSource reconnect delay in ms
        last_sent: dict[str, float] = {}
        while not await request.is_disconnected():
            for update in cache.all():
                if last_sent.get(update.ticker) != update.timestamp:
                    last_sent[update.ticker] = update.timestamp
                    yield f"data: {json.dumps(update.to_dict())}\n\n"
            await asyncio.sleep(PUSH_SECONDS)

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
```

- On connect, every ticker is pushed immediately (initial state), then only changes.
- With the simulator every ticker changes each tick, so ~10 small events per 500ms. With Massive, events burst once per poll.
- Reconnection: the browser `EventSource` reconnects automatically after `retry`. A fresh connection re-sends all tickers, so no `Last-Event-ID` handling is needed.
- No auth, no CORS: same origin.

Frontend consumption (for the frontend agent; shows the contract):

```ts
const es = new EventSource("/api/stream/prices");
es.onopen = () => setStatus("connected");
es.onerror = () => setStatus(es.readyState === EventSource.CONNECTING ? "reconnecting" : "disconnected");
es.onmessage = (e) => {
  const u = JSON.parse(e.data); // {ticker, price, previous_price, change_pct, direction, ...}
  updatePrice(u);               // store latest price + append to sparkline buffer
  flash(u.ticker, u.direction); // add "flash-up"/"flash-down" class, remove after ~500ms
};
```

## 11. Configuration Summary

| Variable | Default | Effect |
|---|---|---|
| `MASSIVE_API_KEY` | empty | Non-empty selects `MassiveSource`; empty selects `SimulatorSource` |
| `MASSIVE_POLL_SECONDS` | `15` | Massive poll interval (free tier: keep >= 15) |

Simulator constants (`TICK_SECONDS`, `TIME_SPEEDUP`, `EVENT_PROB`, `MARKET_WEIGHT`, `SECTOR_WEIGHT`) live as module constants in `simulator.py`; they are tuning knobs, not environment config.

## 12. Tests

`tests/market/` with `pytest-asyncio` (`asyncio_mode = "auto"` in `pyproject.toml`).

```python
# test_cache.py
from app.market import PriceCache

def test_previous_price_and_direction():
    cache = PriceCache()
    cache.update("AAPL", 100.0, prev_close=99.0)
    u = cache.update("AAPL", 101.0)
    assert (u.previous_price, u.prev_close, u.direction) == (100.0, 99.0, "up")
    assert u.change_pct == round(2 / 99 * 100, 3)

def test_remove():
    cache = PriceCache()
    cache.update("AAPL", 100.0)
    cache.remove("AAPL")
    assert cache.get_price("AAPL") is None
```

```python
# test_simulator.py
import math, random
from app.market import PriceCache
from app.market.simulator import DT, SimulatorSource

async def test_seeds_and_steps_stay_positive():
    cache = PriceCache()
    sim = SimulatorSource(cache, rng=random.Random(1))
    for t in ("AAPL", "ZZZZ"):
        await sim.add_ticker(t)
    assert cache.get_price("AAPL") == 190.0
    assert 50 <= cache.get_price("ZZZZ") <= 300
    for _ in range(10_000):
        sim.step()
    assert all(u.price > 0 for u in cache.all())

def test_gbm_log_return_moments():
    """Mean/std of per-step log returns match (mu - sigma^2/2)*dt and sigma*sqrt(dt)."""
    cache = PriceCache()
    sim = SimulatorSource(cache, rng=random.Random(7))
    sim._seed("AAPL")
    logs, prev = [], sim._prices["AAPL"]
    for _ in range(20_000):
        sim.step()
        cur = sim._prices["AAPL"]
        logs.append(math.log(cur / prev))
        prev = cur
    std = (sum((x - sum(logs)/len(logs))**2 for x in logs) / len(logs)) ** 0.5
    assert abs(std - 0.25 * math.sqrt(DT)) / (0.25 * math.sqrt(DT)) < 0.1  # events add a little

async def test_remove_ticker_clears_cache():
    cache = PriceCache()
    sim = SimulatorSource(cache)
    await sim.add_ticker("AAPL")
    await sim.remove_ticker("AAPL")
    assert "AAPL" not in cache and sim.tickers == []

def test_same_sector_more_correlated_than_cross_sector():
    cache = PriceCache()
    sim = SimulatorSource(cache, rng=random.Random(3))
    for t in ("AAPL", "MSFT", "JPM"):
        sim._seed(t)
    series = {t: [] for t in sim.tickers}
    prev = dict(sim._prices)
    for _ in range(20_000):
        sim.step()
        for t in series:
            series[t].append(math.log(sim._prices[t] / prev[t]))
            prev[t] = sim._prices[t]
    def corr(a, b):
        ma, mb = sum(a)/len(a), sum(b)/len(b)
        cov = sum((x-ma)*(y-mb) for x, y in zip(a, b))
        return cov / math.sqrt(sum((x-ma)**2 for x in a) * sum((y-mb)**2 for y in b))
    assert corr(series["AAPL"], series["MSFT"]) > corr(series["AAPL"], series["JPM"]) + 0.15
```

```python
# test_massive.py
import httpx
from app.market import PriceCache
from app.market.massive import MassiveSource, parse_snapshot

SAMPLE = {"status": "OK", "count": 3, "tickers": [
    {"ticker": "AAPL", "lastTrade": {"p": 191.23}, "min": {"c": 191.2},
     "day": {"c": 191.0}, "prevDay": {"c": 190.0}},
    {"ticker": "MSFT", "min": {"c": 420.5}, "day": {}, "prevDay": {"c": 418.0}},   # no lastTrade
    {"ticker": "TSLA", "day": {"c": 0}, "prevDay": {"c": 250.0}},                   # closed market
]}

def test_parse_fallback_chain():
    got = parse_snapshot(SAMPLE)
    assert got == {"AAPL": (191.23, 190.0), "MSFT": (420.5, 418.0), "TSLA": (250.0, 250.0)}

async def test_poll_once_writes_cache_and_sends_tickers_param():
    seen = {}
    def handler(request: httpx.Request) -> httpx.Response:
        seen["tickers"] = request.url.params["tickers"]
        seen["auth"] = request.headers["authorization"]
        return httpx.Response(200, json=SAMPLE)

    client = httpx.AsyncClient(base_url="https://api.massive.com",
                               transport=httpx.MockTransport(handler),
                               headers={"Authorization": "Bearer k"})
    cache = PriceCache()
    src = MassiveSource(cache, "k", client=client)
    src._tickers = {"MSFT", "AAPL", "TSLA"}
    await src.poll_once()
    assert seen == {"tickers": "AAPL,MSFT,TSLA", "auth": "Bearer k"}
    assert cache.get("AAPL").prev_close == 190.0

async def test_poll_failure_keeps_old_prices():
    cache = PriceCache()
    cache.update("AAPL", 100.0)
    client = httpx.AsyncClient(base_url="https://api.massive.com",
                               transport=httpx.MockTransport(lambda r: httpx.Response(429)))
    src = MassiveSource(cache, "k", client=client)
    src._tickers = {"AAPL"}
    await src.poll_once()  # must not raise
    assert cache.get_price("AAPL") == 100.0
```

```python
# test_factory.py
from app.market import PriceCache, create_market_source
from app.market.massive import MassiveSource
from app.market.simulator import SimulatorSource

def test_factory_selects_source(monkeypatch):
    monkeypatch.setenv("MASSIVE_API_KEY", "")
    assert isinstance(create_market_source(PriceCache()), SimulatorSource)
    monkeypatch.setenv("MASSIVE_API_KEY", "abc")
    assert isinstance(create_market_source(PriceCache()), MassiveSource)
```

```python
# test_stream.py - SSE format and change-only pushes
import json
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.market import PriceCache
from app.market.stream import router

def test_sse_first_event_is_a_price():
    app = FastAPI()
    app.state.price_cache = PriceCache()
    app.state.price_cache.update("AAPL", 190.0, prev_close=189.0)
    app.include_router(router)
    with TestClient(app).stream("GET", "/api/stream/prices") as r:
        assert r.headers["content-type"].startswith("text/event-stream")
        lines = r.iter_lines()
        data = next(line for line in lines if line.startswith("data:"))
        assert json.loads(data[5:])["ticker"] == "AAPL"
```

Manual smoke test once the backend runs:

```bash
cd backend && uv run uvicorn app.main:app --port 8000
curl -N http://localhost:8000/api/stream/prices        # simulator: ~10 events / 500ms
MASSIVE_API_KEY=xxx uv run uvicorn app.main:app        # real data: burst every 15s
```

## 13. Implementation Order

Small increments, each verified before the next:

1. `models.py` + `cache.py` + `test_cache.py`.
2. `interface.py` + `seed_data.py` + `simulator.py` + simulator tests.
3. `stream.py` + `test_stream.py`; run uvicorn and `curl -N` the stream.
4. `massive.py` + mocked tests; then one live call with a real key.
5. `factory.py`, `__init__.py`, lifespan wiring in `main.py`.
6. Watchlist and trade routes use `add_ticker` / `remove_ticker` / `get_price`.

## 14. Decisions and Open Questions

| Decision | Reason |
|---|---|
| `httpx` instead of the `massive` SDK | One endpoint is needed; async-native; easy to mock; no sync-in-thread wrapper |
| One event per ticker, change-only | Matches the PLAN's per-event fields; keeps the frontend handler trivial |
| Cache stamps its own time | Avoids nanosecond/millisecond unit differences between plans |
| Factor-mix correlation instead of Cholesky | No numpy dependency; exact unit variance; correlation structure is easy to read and tune |
| `prev_close` as seed price in the simulator | "Daily change %" needs a baseline; there is no real prior close |

Open questions for the user:

- Should adding a ticker that Massive does not know be rejected (needs a price after the first poll), or silently listed with no price?
- Should removing a watchlist ticker that has an open position keep it streaming? (Design assumes yes.)
- Is the 30x time speedup acceptable for demo feel, or should simulated moves be closer to real-time volatility?
