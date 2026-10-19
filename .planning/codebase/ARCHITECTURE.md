---
last_mapped_commit: 24a4b2a30df1d0f61a24990f210bc270e83cd728
last_mapped_at: 2026-10-19
---
<!-- refreshed: 2026-10-19 -->

# Architecture

**Analysis Date:** 2026-10-19

## Current Scope

Only the market data layer is implemented. The repo contains `backend/` (FastAPI, `uv` project) and `planning/` (docs). The frontend, SQLite layer, portfolio/trade logic, watchlist API, chat/LLM integration, and Docker/scripts described in `planning/PLAN.md` do not exist yet. This document describes what exists and marks the planned parts as such.

## System Overview

```text
┌──────────────────────────────────────────────────────────────┐
│  FastAPI app  `backend/app/main.py`  (lifespan + routers)     │
│   GET /api/health            (inline handler in main.py)     │
│   GET /api/stream/prices     (`backend/app/market/stream.py`)│
└───────────────┬──────────────────────────────┬───────────────┘
                │ reads                        │ owns lifecycle
                ▼                              ▼
┌──────────────────────────────┐   ┌─────────────────────────────┐
│ PriceCache                   │◄──│ MarketDataSource (ABC)      │
│ `app/market/cache.py`        │   │ `app/market/interface.py`   │
│ in-memory latest PriceUpdate │   ├─────────────────────────────┤
└──────────────────────────────┘   │ SimulatorSource (default)   │
                                   │ `app/market/simulator.py`   │
                                   │ MassiveSource (REST poll)   │
                                   │ `app/market/massive.py`     │
                                   └──────────────┬──────────────┘
                                                  │ chosen by
                                   `app/market/factory.py` (env)
```

Single process, single event loop. Background producers write into one shared in-memory cache. Request handlers only read from it.

## Pattern Overview

**Overall:** Layered service with a producer/cache/consumer pipeline inside one ASGI process. Strategy pattern for the market data source.

**Key Characteristics:**
- One process, one event loop (`asyncio`). The cache has no locks; `backend/app/market/cache.py` documents this.
- Producers (`SimulatorSource`, `MassiveSource`) run as background `asyncio` tasks started in the FastAPI lifespan.
- Consumers (SSE endpoint) poll the cache on a fixed interval rather than receiving pushes from producers.
- Source selection is by environment variable at startup, not per request.
- Data is in memory only. No database is wired yet (`planning/PLAN.md` specifies SQLite at `db/finally.db`).

## Layers

**Application / Composition Root:**
- Purpose: Build the cache, pick the source, start and stop it, mount routers.
- Location: `backend/app/main.py`
- Contains: `lifespan` async context manager, `FastAPI` instance `app`, `/api/health` route.
- Depends on: `app.market` (package exports), `app.market.seed_data.DEFAULT_TICKERS`, `app.market.stream.router`.
- Used by: uvicorn (entry point), tests in `backend/tests/market/test_app.py`.

**Market Data Public API:**
- Purpose: Single import surface for the market package.
- Location: `backend/app/market/__init__.py`
- Contains: re-exports `MarketDataSource`, `PriceCache`, `PriceUpdate`, `create_market_source`.
- Depends on: `cache`, `factory`, `interface`, `models`.
- Used by: `app/main.py`.

**Market Data Abstraction:**
- Purpose: Define the contract every source implements.
- Location: `backend/app/market/interface.py`
- Contains: abstract `MarketDataSource` with `start`, `stop`, `add_ticker`, `remove_ticker`, and the `tickers` property.
- Depends on: nothing in-app.
- Used by: `simulator.py`, `massive.py`, `factory.py`.

**Market Data Producers:**
- Purpose: Generate or fetch prices and write them into `PriceCache`.
- Location: `backend/app/market/simulator.py` (GBM simulator), `backend/app/market/massive.py` (Massive REST poller).
- Contains: `SimulatorSource`, `MassiveSource`, `parse_snapshot` (pure function in `massive.py`).
- Depends on: `PriceCache`, `MarketDataSource`, `seed_data`; `httpx` for Massive.
- Used by: `factory.py` via `create_market_source`.

**Shared State (Price Cache):**
- Purpose: Hold the latest `PriceUpdate` per ticker.
- Location: `backend/app/market/cache.py`
- Contains: `PriceCache` with `update`, `get`, `get_price`, `all`, `remove`, `__contains__`.
- Depends on: `models.PriceUpdate`.
- Used by: all producers (writes), `stream.py` and `main.py` (reads).

**Domain Model:**
- Purpose: Immutable price snapshot with derived fields.
- Location: `backend/app/market/models.py`
- Contains: frozen, slotted dataclass `PriceUpdate` with `direction`, `change_pct`, `to_dict()`.
- Depends on: nothing.
- Used by: cache, producers, SSE serializer.

**Transport (SSE):**
- Purpose: Stream cache contents to browser clients.
- Location: `backend/app/market/stream.py`
- Contains: `APIRouter(prefix="/api/stream")`, `price_events` async generator, `stream_prices` route.
- Depends on: `PriceCache`, `PriceUpdate`, FastAPI's `fastapi.sse` (`EventSourceResponse`, `ServerSentEvent`).
- Used by: mounted in `app/main.py`; consumed by `scripts/watch_prices.py` and, later, the frontend.

**Static Configuration Data:**
- Purpose: Default tickers, seed prices, GBM drift/volatility, sector groups.
- Location: `backend/app/market/seed_data.py`
- Contains: `DEFAULT_TICKERS`, `SEED_PRICES`, `GBM_PARAMS`, `DEFAULT_PARAMS`, `SECTORS`.
- Used by: `simulator.py`, `main.py`.

## Data Flow

### Primary Price Path (simulator)

1. `lifespan` in `backend/app/main.py` creates `PriceCache()` and calls `create_market_source(cache)`.
2. `create_market_source` in `backend/app/market/factory.py` returns `SimulatorSource(cache)` when `MASSIVE_API_KEY` is empty.
3. `source.start(DEFAULT_TICKERS)` seeds each ticker in `SimulatorSource._seed` (calls `cache.update(..., prev_close=price)`) and creates the `_run` task.
4. `_run` calls `step()` every `TICK_SECONDS = 0.5` (`backend/app/market/simulator.py`). Each step applies GBM with correlated market/sector shocks and occasional jump events, rounds to 2 decimals, and calls `cache.update`.
5. Each `cache.update` creates a new `PriceUpdate` object with `previous_price` set from the old entry (`backend/app/market/cache.py`).
6. `price_events` in `backend/app/market/stream.py` runs every `PUSH_SECONDS = 0.5`, iterates `cache.all()`, and yields only updates whose object identity differs from the last one sent for that ticker.
7. `stream_prices` yields those events as SSE over `GET /api/stream/prices`. Each event body is `PriceUpdate.to_dict()` (ticker, price, previous_price, prev_close, change_pct, direction, timestamp).

### Price Path (Massive)

1. Same as steps 1 to 2 above, but the factory returns `MassiveSource(cache, api_key, poll_seconds)` where `poll_seconds` comes from `MASSIVE_POLL_SECONDS` (default 15).
2. `MassiveSource` polls `SNAPSHOT_PATH` on `BASE_URL = "https://api.massive.com"` for the union of tracked tickers. `parse_snapshot` maps the response to `{ticker: (price, prev_close)}`, falling back from last trade to minute close, day close, then previous close.
3. Results are written to the cache. From step 6 onward, the path is identical to the simulator.

### Shutdown

`lifespan` awaits `source.stop()` after `yield`. Each source cancels its task and suppresses `CancelledError`.

**State Management:**
- Server state: `app.state.price_cache` and `app.state.market_source`, set in `lifespan`. Route handlers read `request.app.state.price_cache`.
- Client state: none on the server. The SSE sender tracks `last_sent` per connection.
- Persistent state: none yet.

## Key Abstractions

**MarketDataSource:**
- Purpose: Swap simulator and real data without changing downstream code.
- Examples: `backend/app/market/interface.py`, `backend/app/market/simulator.py`, `backend/app/market/massive.py`
- Pattern: Abstract base class with async lifecycle methods (`start`/`stop`) and ticker management (`add_ticker`/`remove_ticker`, both idempotent per the docstring).

**PriceCache:**
- Purpose: Single source of latest prices shared by producers and readers.
- Examples: `backend/app/market/cache.py`
- Pattern: Plain in-memory dict. Identity of `PriceUpdate` objects is used as the change marker for SSE.

**PriceUpdate:**
- Purpose: Immutable snapshot used for both transport and UI direction (flash) and daily change %.
- Examples: `backend/app/market/models.py`
- Pattern: Frozen slotted dataclass with derived properties.

**Factory:**
- Purpose: Environment-based selection of the source implementation.
- Examples: `backend/app/market/factory.py`
- Pattern: Function that returns the interface type.

## Entry Points

**ASGI application:**
- Location: `backend/app/main.py` (`app = FastAPI(lifespan=lifespan)`)
- Triggers: `uvicorn app.main:app` run from `backend/`. The planned Dockerfile CMD is not yet present.
- Responsibilities: start/stop market source, serve `/api/health` and `/api/stream/prices`.

**Health check:**
- Location: `backend/app/main.py` (`GET /api/health`)
- Triggers: HTTP GET.
- Responsibilities: returns `{"status": "ok"}`.

**Watch script (developer tool):**
- Location: `backend/scripts/watch_prices.py`
- Triggers: `uv run scripts/watch_prices.py [base_url]` as an external SSE client.
- Responsibilities: render a live terminal table from the SSE stream using `httpx` and `rich`.

## Architectural Constraints

- **Threading:** Single asyncio event loop. Producers and the SSE generator share the cache without locks. Any blocking call in `step()` or the Massive poll loop would stall streaming.
- **Global state:** `app` in `backend/app/main.py` is a module-level singleton. `app.state` holds the cache and source for the process.
- **Circular imports:** None observed. Dependency direction is `main -> market.stream -> market.cache/models`, and `factory -> simulator/massive -> interface/cache`.
- **Single-user assumption:** `DEFAULT_TICKERS` is the only watchlist. `lifespan` has a TODO to use watchlist union open positions from SQLite.
- **Source is process-wide:** One source per process. Switching requires restart.

## Anti-Patterns

### Hard-coded initial ticker list

**What happens:** `backend/app/main.py` passes `DEFAULT_TICKERS` to `source.start` regardless of any runtime watchlist.
**Why it's wrong:** `add_ticker`/`remove_ticker` exist on the interface but nothing calls them, so watchlist changes from the API or chat cannot reach the source.
**Do this instead:** When the watchlist API lands, call `source.add_ticker` and `source.remove_ticker` from those handlers, and build the initial list from the database as the TODO in `main.py` describes.

### Route-level data access through `app.state`

**What happens:** `stream.py` reads `request.app.state.price_cache` directly.
**Why it's wrong:** Handlers depend on untyped attributes set in lifespan. A missing attribute fails at request time.
**Do this instead:** Keep this pattern only while the surface is small. Otherwise add a FastAPI dependency function that returns the cache.

### SSE change detection by object identity

**What happens:** `price_events` in `backend/app/market/stream.py` sends an update when `last_sent[ticker] is not update`.
**Why it's wrong:** It relies on every `cache.update` creating a new object. Any future code that mutates or caches `PriceUpdate` differently will silently stop streaming changes.
**Do this instead:** Keep `PriceUpdate` frozen and created only in `PriceCache.update`, or switch to a version counter in the cache.

## Error Handling

**Strategy:** Minimal. Producers and the SSE loop do not catch errors around the main loop.

**Patterns:**
- `SimulatorSource.stop` suppresses `asyncio.CancelledError` only.
- `parse_snapshot` skips entries with no usable price instead of raising.
- Massive HTTP errors are handled inside `backend/app/market/massive.py` (see the module for the polling loop).

## Cross-Cutting Concerns

**Logging:** `massive.py` uses `logging.getLogger(__name__)`. No logging configuration exists in the app.
**Validation:** Not yet implemented at the API layer (no request bodies exist).
**Authentication:** None. `planning/PLAN.md` specifies no login. Massive uses a bearer token from `MASSIVE_API_KEY`.

## Planned but Not Yet Present

Per `planning/PLAN.md`, these layers are specified but have no code yet:
- SQLite persistence (`backend/db/`, runtime file `db/finally.db`)
- Portfolio and trade execution, portfolio snapshot task (every 30 s)
- Watchlist REST endpoints and portfolio REST endpoints
- Chat endpoint with LiteLLM -> OpenRouter and structured trade output
- Next.js frontend in `frontend/` served as a static export from FastAPI

---

*Architecture analysis: 2026-10-19*
