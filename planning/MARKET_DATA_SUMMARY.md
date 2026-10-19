# Market Data - Summary

Status: **complete and tested** (54 tests pass, Python 3.12, FastAPI 0.143.1). Code lives in `backend/app/market/`.

This is the short reference for agents building the rest of FinAlly. Details:
- `PLAN.md` sections 5, 6, 8 - the contract
- `MARKET_DATA_DESIGN.md` - full design with code
- `MARKET_DATA_REVIEW.md` - code review and how each finding was resolved
- `UNDERSTANDING.md` - plain-language explanation of the whole system

## 1. Architecture

```
SimulatorSource (GBM, 500ms)      MassiveSource (REST poll, 15s)
              \                      /
               implements MarketDataSource
                         | writes
                         v
                    PriceCache  (latest + previous price per ticker)
                         | reads
   SSE /api/stream/prices | trades | watchlist | portfolio | chat context
```

Rules:
- Sources only **write** to the cache. Everything else only **reads** it. Nothing downstream knows which source is active.
- Everything runs on one asyncio event loop, so the cache has no locks.
- The source is chosen once at startup from `MASSIVE_API_KEY`.
- The source owns the set of tracked tickers (`add_ticker` / `remove_ticker`).

## 2. Modules

| File | Purpose |
|---|---|
| `models.py` | `PriceUpdate` frozen dataclass: `ticker`, `price`, `previous_price`, `prev_close`, `timestamp`; derived `direction` (`up`/`down`/`flat`) and `change_pct` (vs `prev_close`); `to_dict()` |
| `cache.py` | `PriceCache`: `update`, `get`, `get_price`, `all`, `remove`, `in` |
| `interface.py` | `MarketDataSource` ABC: `start(tickers)`, `stop()`, `add_ticker`, `remove_ticker`, `tickers` |
| `seed_data.py` | `DEFAULT_TICKERS`, seed prices, per-ticker GBM params, sectors |
| `simulator.py` | `SimulatorSource` (default) |
| `massive.py` | `MassiveSource` + `parse_snapshot` |
| `factory.py` | `create_market_source(cache)` |
| `stream.py` | `GET /api/stream/prices` router and `price_events()` generator |
| `app/main.py` | Lifespan: builds cache + source, starts it, stores both on `app.state`; also `GET /api/health` |

Public imports: `from app.market import PriceCache, PriceUpdate, MarketDataSource, create_market_source`.

## 3. Simulator (default)

- Geometric Brownian motion, exact form: `S_next = S * exp((mu - sigma^2/2) dt + sigma sqrt(dt) z)`. Prices stay positive.
- Tick every 0.5s. Time runs 30x faster than a real trading year (`TIME_SPEEDUP`) so moves are visible in a demo.
- Correlation via a factor mix with unit variance: `z = sqrt(0.3) Z_market + sqrt(0.3) Z_sector + sqrt(0.4) noise`. Measured correlation: ~0.6 within a sector, ~0.3 across sectors.
- Random events: probability 0.0005 per ticker per tick of a 2-5% jump up or down.
- Seed prices: AAPL 190, GOOGL 175, MSFT 420, AMZN 185, TSLA 250, NVDA 120, META 500, JPM 200, V 275, NFLX 650. Unknown tickers get a random seed in [50, 300] and default params (mu 0.05, sigma 0.30).
- Sectors: tech (8 tickers) and finance (JPM, V).
- `prev_close` = seed price, so "daily change %" is change since seeding.
- Internal prices are unrounded; only cache writes are rounded to cents.

## 4. Massive API (optional)

- Used when `MASSIVE_API_KEY` is set and non-empty (whitespace counts as empty).
- One request per poll for all tickers: `GET https://api.massive.com/v2/snapshot/locale/us/markets/stocks/tickers?tickers=...` with `Authorization: Bearer <key>`. Watchlist size does not affect the rate limit.
- Poll interval: `MASSIVE_POLL_SECONDS`, default 15 (free tier: 5 calls/min).
- Price fallback: `lastTrade.p` -> `min.c` -> `day.c` -> `prevDay.c`. `prev_close` = `prevDay.c`.
- Uses `httpx.AsyncClient` (not the Massive SDK). The cache stamps its own time instead of using the payload timestamps.
- Any poll error (HTTP, bad JSON, unexpected payload) is logged and skipped; polling continues and old prices stay in the cache.
- `start()` awaits the first poll so the first SSE push has data. Startup can take up to the 10s client timeout.
- Verified only against mocked responses; no live call with a real key yet.

## 5. SSE Stream

`GET /api/stream/prices`, built on FastAPI's native `fastapi.sse.EventSourceResponse`.

- First event: `retry: 1000`. Then every ticker once (initial state), then only tickers that changed, checked every 0.5s.
- Change detection uses `PriceUpdate` object identity (every cache write creates a new object).
- Keep-alive `: ping` comment after 15s of silence; `Cache-Control: no-cache`, `X-Accel-Buffering: no`; generator is cancelled on client disconnect.
- One event per ticker:

```json
{"ticker": "AAPL", "price": 191.23, "previous_price": 191.10, "prev_close": 190.0,
 "change_pct": 0.647, "direction": "up", "timestamp": 1760000000.123}
```

- Simulator: ~10 events every 500ms. Massive: one burst per poll.

## 6. Contract for Other Agents

**Backend (database, trading, watchlist, chat):**
- Read prices with `request.app.state.price_cache.get_price(ticker)`. It returns `None` when there is no price yet (new Massive ticker, unknown symbol): return HTTP 400 "No price available", do not crash.
- Watchlist add: `await app.state.market_source.add_ticker(ticker)`. Remove: only call `remove_ticker` if the user holds no position in it, so held positions keep their price.
- Tickers must be upper case; the API layer normalizes them.
- Chat-driven trades and watchlist changes must use the same helpers as the REST routes.
- **TODO:** `main.py` lifespan starts with `DEFAULT_TICKERS`. Replace with "watchlist UNION open positions" from SQLite when the database is built.

**Frontend:**
- Use `EventSource("/api/stream/prices")`. Status dot: `onopen` -> green; `onerror` with `readyState === CONNECTING` -> yellow, else red.
- On each message: update the price, append to the sparkline buffer, flash using `direction`.
- Removals are **not** streamed. After add/remove, refresh from `GET /api/watchlist` and drop missing tickers from state.
- A reconnect re-sends all tickers; no `Last-Event-ID` handling needed.

## 7. Known Behaviors (by design)

- Removing and re-adding a simulated ticker re-seeds its price (e.g. AAPL back to 190.00). Affects watch-only tickers only.
- With Massive, a newly added ticker has no price until the next poll (up to 15s), and prices flash every ~15s instead of every 500ms.
- With Massive, stale prices are not re-pushed; the keep-alive ping holds the connection open.

## 8. Configuration

| Variable | Default | Effect |
|---|---|---|
| `MASSIVE_API_KEY` | empty | Non-empty selects Massive, else the simulator |
| `MASSIVE_POLL_SECONDS` | `15` | Massive poll interval |

Simulator tuning constants (`TICK_SECONDS`, `TIME_SPEEDUP`, `EVENT_PROB`, `MARKET_WEIGHT`, `SECTOR_WEIGHT`) are module constants in `simulator.py`, not env config.

## 9. Running and Testing

From `backend/`:

```bash
uv sync
uv run pytest                                              # 54 tests
uv run --env-file ../.env uvicorn app.main:app --port 8000
curl -N http://localhost:8000/api/stream/prices
uv run scripts/watch_prices.py                             # live terminal board (rich)
```

Tests (`tests/market/`): cache/models, simulator (exact drift, volatility, correlation, events, seeding), Massive (parsing, fallbacks, error resilience, mocked transport), factory, stream (change-only pushes, real-HTTP stream with headers and ping), app lifespan.

## 10. Open Questions

- Should adding a ticker Massive does not know be rejected, or listed with no price?
- Is the 30x time speedup right for demo feel, or should volatility be closer to real time?
