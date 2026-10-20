# Architecture Research

**Domain:** AI-assisted trading-practice workstation (single user, single container, brownfield on a finished market-data layer)
**Researched:** 2026-10-19
**Confidence:** HIGH for backend structure and data flow (grounded in the existing code); MEDIUM for two library details flagged "verify" below

Scope: how the remaining PLAN.md features plug into the existing FastAPI app (`backend/app/main.py`, `backend/app/market/*`). Rule applied throughout: simple, short modules, no over-engineering, one event loop.

---

## Standard Architecture

### System Overview

```
 Browser (Next.js static export, one page)
 ┌───────────────────────────────────────────────────────────────────────┐
 │ price store (zustand)        portfolio store (zustand)                 │
 │  prices{}, history{}, status  portfolio, trades, watchlist, snapshots  │
 │  ^ EventSource                ^ fetch /api/*          derive.ts (live  │
 │  |                            |                      P&L = REST state │
 │  |                            |                      x live prices)   │
 └──┼────────────────────────────┼───────────────────────────────────────┘
    | SSE batch (2 Hz)           | REST (on mount, after trade/chat)
 ┌──┼────────────────────────────┼───────────────────────────────────────┐
 │  |   FastAPI  app/main.py = composition root only                      │
 │  |   routes/ (thin)  ->  services/ (all rules)  ->  db/ repos (SQL)    │
 │  |        |                  |                        |                │
 │  |        |                  |                        v                │
 │  |        |                  |                  SQLite  db/finally.db  │
 │  |        |                  v                                         │
 │  |        |        market/ PriceCache  <--writes--  MarketDataSource   │
 │  v        v                  ^                      (sim | massive)    │
 │ market/stream.py ------------+ reads (version-gated batch)            │
 │ StaticFiles("/") mounted LAST -> frontend export (index.html, _next/)  │
 │ background tasks: market source task, snapshot_loop (30 s)             │
 └───────────────────────────────────────────────────────────────────────┘
        services/llm.py --acompletion--> OpenRouter (or LLM_MOCK stub)
```

Dependency direction (strict, one way): `routes -> services -> db repos` and `services -> market (cache, source)`. `market/` imports nothing from `db/` or `services/`. The union "watchlist + positions" therefore lives in a service, not in the market package.

### Component Responsibilities

| Component | Responsibility | Talks to |
|-----------|----------------|----------|
| `main.py` | Lifespan: open DB, resolve and start market source, start snapshot task, build `Context`; include routers; mount static last | everything (wiring only, no logic) |
| `context.py` | Frozen dataclass `Context(db, cache, source, market_note)` stored once at `app.state.ctx`; one `get_ctx(request)` dependency | routes, services |
| `config.py` | Env reads: `DB_PATH`, `STATIC_DIR`, `LLM_MOCK`, `STARTING_CASH = 10000.0` | all |
| `schemas.py` | Pydantic models: `Ticker` type (normalise upper + regex), `TradeRequest`, `WatchlistAdd`, `ChatRequest`, `ChatResult`, `LLMReply` (the structured-output schema) | routes, services |
| `db/connection.py` | `connect(path)`, `init_db(conn)` lazy create (`CREATE TABLE IF NOT EXISTS`) + seed | main, tests |
| `db/*.py` repos (profile, watchlist, positions, trades, snapshots, chat) | SQL only, plain functions taking `conn`, return dicts/rows. No business rules, no commit decisions | services |
| `services/tracking.py` | `tracked_tickers(conn)` = watchlist U positions; `sync(ctx)` reconciles `source.tickers` to that set | trading, watchlist, main |
| `services/trading.py` | `execute_trade(ctx, ticker, side, qty)`: the ONE place trades happen (route and chat both call it); raises `TradeError` | repos, cache, tracking, snapshots |
| `services/portfolio.py` | `build_portfolio(ctx)`: positions priced from cache, cash, total, unrealized, realized (SUM column) | repos, cache |
| `services/watchlist.py` | add/remove ticker then `tracking.sync` (route and chat both call it) | repos, tracking |
| `services/snapshots.py` | `record_snapshot(ctx)`, `snapshot_loop(ctx)` (30 s) | repos, cache |
| `services/chat.py` | Build context, call LLM, parse, execute actions, persist, return | llm, trading, watchlist, portfolio, repos |
| `services/llm.py` | `async call_llm(messages) -> LLMReply`; LiteLLM `acompletion` or deterministic mock | OpenRouter |
| `routes/*.py` | Parse request model, call one service, map `TradeError` to HTTP 400 | services |
| `market/*` (existing) | Produce prices; small additions listed below | cache |
| `market/stream.py` | Version-gated, batched SSE of the full price snapshot + market status | cache, source |

---

## Recommended Project Structure

```
backend/app/
├── main.py                 # lifespan + include_router + static mount (target <60 lines)
├── context.py  config.py  schemas.py
├── db/                     # NOTE: under app/, NOT backend/db (see Pitfall below)
│   ├── schema.sql          # all 6 tables, IF NOT EXISTS
│   ├── connection.py       # connect + init_db (+ seed gate)
│   └── profile.py watchlist.py positions.py trades.py snapshots.py chat.py
├── services/
│   └── tracking.py trading.py portfolio.py watchlist.py snapshots.py chat.py llm.py
├── routes/
│   └── portfolio.py watchlist.py chat.py system.py
└── market/                 # existing; stream.py gets batching, cache.py gets `version`

frontend/src/
├── app/                    # layout.tsx, page.tsx (single route), globals.css
├── lib/                    # api.ts (typed fetch), types.ts, derive.ts (pure math), format.ts
├── store/                  # prices.ts (SSE + sparkline history + status), portfolio.ts (REST data + actions)
├── hooks/                  # usePriceStream.ts (mounted once in page.tsx)
└── components/             # Header, Watchlist, Sparkline, MainChart, Heatmap, PnlChart,
                            # PositionsTable, Blotter, TradeBar, ChatPanel, Tip (jargon tooltip)
```

### Structure Rationale

- **`backend/app/db/` instead of PLAN.md's `backend/db/`:** PLAN.md section 11 mounts the named volume at `/app/db`. If `backend/` is copied to `/app`, `backend/db/` (Python schema code) and the runtime volume collide: Docker seeds an empty named volume from image contents on first mount, so stale schema code would persist in the volume across rebuilds. Keeping code under `app/db/` and pointing `DB_PATH` (set via `ENV` in the Dockerfile) at the volume removes the whole class of problem. Minor deviation from PLAN section 4; record as a decision.
- **Repos as many tiny files:** matches the "short modules" rule and keeps each service test to one fake `conn` (`sqlite3.connect(":memory:")`).
- **Services own rules, routes stay thin:** the chat path must run the same validation as the manual path, which only works if validation lives below both.

---

## Architectural Patterns

### Pattern 1: Single `Context` object, one dependency

**What:** One frozen dataclass holds `db`, `cache`, `source`, `market_note`. Set in lifespan, fetched via `get_ctx`. Services take `ctx` as first argument.
**When:** Always here; resolves the `app.state` anti-pattern in ARCHITECTURE.md/CONCERNS.md without a DI framework.
**Trade-offs:** Tiny global-ish bag; tests build a `Context` with an in-memory DB and a fake source. Existing `stream.py` still reads `app.state.price_cache`; switch it to `ctx.cache` when it is touched for batching.

```python
@dataclass(frozen=True)
class Context:
    db: sqlite3.Connection
    cache: PriceCache
    source: MarketDataSource
    market_note: str | None   # e.g. "Massive key rejected, using simulator"

def get_ctx(request: Request) -> Context:
    return request.app.state.ctx
```

### Pattern 2: One sqlite3 connection, sync repos, `async def` routes

**What:** stdlib `sqlite3`, one connection created in lifespan (`PRAGMA journal_mode=WAL`), used only from the event-loop thread. Routes are `async def` and call sync services. Repos never open their own connection.
**Why it is safe:** queries on a local SQLite file take well under a millisecond, and with no `await` between "read price, validate, write rows" the whole trade is atomic with respect to every other request, the SSE generator, the simulator and the snapshot task. No locks, no `aiosqlite`, no connection pool.
**Hard rule:** never declare these routes as plain `def` (FastAPI would run them in a threadpool and the shared connection plus the no-await atomicity argument both break). The only `await` in `execute_trade` is the final `tracking.sync`, after commit.
**Trade-offs:** a very slow query would stall streaming; irrelevant at this data size.

### Pattern 3: Reconciler for market tracking (not per-event add/remove)

**What:** `tracking.sync(ctx)` computes `desired = watchlist U positions` from SQLite, compares with `source.tickers`, awaits `add_ticker` for missing and `remove_ticker` for extras. Called after: watchlist add/remove, any trade that opens or closes a position, and once at startup (`source.start(sorted(tracked))`).
**When:** every state change that can alter the set.
**Why:** idempotent and impossible to get wrong in the "removed from watchlist but still holding it" case (price must keep streaming, so the ticker stays; and "sold the last share of a non-watchlist ticker" removes it). Both `add_ticker`/`remove_ticker` are already idempotent.

```python
async def sync(ctx: Context) -> None:
    desired = tracked_tickers(ctx.db)
    current = set(ctx.source.tickers)
    for t in desired - current:
        await ctx.source.add_ticker(t)
    for t in current - desired:
        await ctx.source.remove_ticker(t)
```

### Pattern 4: Version-gated batched SSE with a status envelope

**What:** Add `version: int` to `PriceCache` (incremented in `update` and `remove`; 2 lines). The stream generator sends one event per change containing the FULL snapshot plus market status; the payload is built once per `(version, stale)` key and shared by all clients.
**Event shape (the frontend contract):**

```json
{"prices": [{"ticker":"AAPL","price":190.1,"previous_price":190.0,"prev_close":189.0,
             "change_pct":0.58,"direction":"up","timestamp":1760000000.5}],
 "status": {"source":"simulated|live","stale":false,"note":null}}
```

**Why full snapshot, not a diff:** removes the concerns "removed tickers silently dropped" (client replaces its map; missing ticker disappears) and "unbounded `last_sent`" (no per-connection dict) in one move, and replaces fragile object-identity change detection with the version counter. 10 tickers x ~130 bytes x 2 Hz is negligible.
**Trigger:** send when `(cache.version, stale)` changes; fastapi.sse keepalive pings cover idle Massive intervals. Stale is time-based, so include it in the key so the flip is pushed.
**Verify during implementation:** how `fastapi.sse.ServerSentEvent` accepts a pre-serialised string (check for `raw_data` vs `data`) so the shared payload is not re-serialised per client.

```python
_memo: tuple[tuple, str] | None = None
def batch_payload(ctx) -> tuple[tuple, str]:
    key = (ctx.cache.version, market_status(ctx).stale)
    global _memo
    if _memo is None or _memo[0] != key:
        _memo = (key, json.dumps({"prices": [u.to_dict() for u in ctx.cache.all()],
                                  "status": market_status(ctx)._asdict()}))
    return _memo
```

### Pattern 5: Massive validation with zero extra API calls, then fixed for the session

**What:** `MassiveSource.start()` already primes with one real snapshot request. A new factory function `start_market_source(cache, tickers)` does: if key set, build `MassiveSource`, `await start(tickers)`; if `cache.all()` is empty afterwards (HTTP error, 401/403, tier without snapshots, empty/unparseable body) then `await stop()` and start `SimulatorSource` instead, returning a human note. Costs 1 request, within the free-tier budget (4/min at 15 s polling leaves 1/min headroom).
**Edge:** if the tracked set is empty at startup, probe with `["AAPL"]` or `poll_once` returns early and a valid key looks invalid.
**Status:** add `kind` ("live"/"simulated") and `last_ok` (set in `poll_once` on a successful parse) to the sources. `stale = kind == "live" and now - last_ok > 3 * poll_seconds`. "Stale" means "the API is failing", not "market closed" (frozen weekend prices with successful polls are NOT stale; the badge says LIVE). Do not flip source mid-session (restart to retry); outages show as stale instead.
**Consequence for trading:** a ticker with no cache price (unknown symbol on Massive, or not yet polled) must reject trades ("no price available"). Recommend also rejecting trades while `stale` (one `if`; avoids filling at an hours-old price); confirm in requirements.

### Pattern 6: Client derives live numbers; server is authoritative at rest

**What:** `GET /api/portfolio` returns cash, positions (qty, avg_cost), `realized_pnl`, `total_value` at fetch time. Between fetches the client recomputes market value, unrealized P&L, weights and header total from `positions x live prices` in `lib/derive.ts` (pure functions). The portfolio store refetches only on mount, after a trade, and after a chat reply, never per tick.
**Why:** a live header total with no per-tick server work and no second stream. Cost: the formula exists twice (Python for snapshots, chat context, tests; TypeScript for display). Mitigate with the invariant test below and shared numeric fixtures.
**Invariant (use as a test in both languages):** with no fees, `total_value - 10000 == realized_pnl + unrealized_pnl`.

---

## Realized P&L: store on the trade row (decision)

**Decision:** add `realized_pnl REAL` (NULL for buys) to `trades`, computed inside `execute_trade` at sell time using the position's `avg_cost` before the sell:

```
sell:  realized_pnl = (price - avg_cost) * qty        (avg_cost unchanged after a partial sell)
buy:   new_avg = (old_qty*old_avg + qty*price) / (old_qty + qty)
```

Total realized = `SELECT COALESCE(SUM(realized_pnl),0) FROM trades` (one query in `db/trades.py`).

**Why stored beats derived:** `trades` is append-only and does not record the average cost at the time of the sale, so deriving later means replaying the full trade log in order with the same rounding rules (slow to explain, easy to drift, and wrong the moment any rule changes). Storing it freezes the number the learner was shown at the moment of the sale, makes the blotter row and the AI trade review read straight from data, and costs one nullable column. It is an additive deviation from PLAN.md section 7: put it in `schema.sql` from day one (no DB exists yet, so no migration is needed; adding a column to an existing file later WOULD need a migration since init is `IF NOT EXISTS`).

**Unrealized and blotter "outcome so far" are derived live, never stored:** buy row outcome = `(current_price - price) * qty` (simplification: after a partial sell this still marks the original buy quantity; acceptable and explainable); sell row outcome = its stored `realized_pnl`. Compute client-side from `GET /api/portfolio/trades` + live prices; chat context builder computes the same server-side for the "review my trades" prompt.

**Rules:** delete the `positions` row when quantity falls below 1e-9 (fractional shares); round cash and avg_cost to 4 decimals at write time (PLAN keeps REAL).

---

## Data Flow

### Request Flow: trade -> db -> snapshot -> UI refresh

```
TradeBar (buy/sell click)
  -> store.trade(req)  ->  POST /api/portfolio/trade   (routes/portfolio.py: parse TradeRequest)
       -> services.trading.execute_trade(ctx, ...)      [steps 1-5 contain no await]
          1. price = cache.get_price(ticker)            reject if None or market stale
          2. validate: qty > 0; buy needs cash >= cost; sell needs held >= qty
          3. one SQL transaction: cash, upsert/delete position, insert trade (+realized_pnl)
          4. record_snapshot(ctx)  (total value after the trade)  -> returned point
          5. build feedback: cash_before/after, new avg_cost, weight_pct
          6. await tracking.sync(ctx)   (new/closed position may change tracked set)
  <- 200 {trade, feedback, portfolio, snapshot}   or  400 {detail: "Not enough cash ..."}
  store: set portfolio, prepend trade, append snapshot to history, show feedback toast
  derived selectors recompute header, positions, heatmap, markers automatically
```

The response carries `portfolio` and `snapshot` so the UI needs zero follow-up requests after a manual trade.

### State Management

```
price store (zustand)                           portfolio store (zustand)
  prices{ticker: PriceUpdate}  <- SSE batch        portfolio, trades[], watchlist[], snapshots[]
  history{ticker: [t,price]}   <- append per batch  actions: load(), trade(), addTicker(), removeTicker(), chat()
  status{source, stale, note}  <- SSE batch         every action ends by setting server-returned state
  connection: ok|reconnecting|down <- EventSource
        \                                   /
         derive.ts selectors (pure): positionsView, totalValue, unrealized, weights, tradeOutcomes
                         |
           components subscribe with narrow selectors (s => s.prices[ticker])
```

**Why zustand:** prices change twice a second, and React Context would re-render the whole tree each tick. Zustand selectors re-render only the rows whose slice changed, there is no provider boilerplate, and it is ~1 KB. Two small stores (not one) keep high-frequency and low-frequency data apart. Plain `fetch` in store actions; no TanStack Query/SWR needed (nothing is cached or polled; mutations return fresh state).

**SSE client:** native `EventSource` created in one hook mounted once (`'use client'`, inside `useEffect`, never at module scope because the export prerenders). `onopen` -> connected (green); `onerror` with `readyState === CONNECTING` -> reconnecting (yellow); `CLOSED` -> down (red). On each message: replace `prices` with the batch, and for each ticker append to `history[ticker]` only if `timestamp` differs from the last stored point (dedupes Massive batches that repeat 15 s data), cap ~300 points, drop history for tickers missing from the batch.

**Flash animation without timers:** render the price cell with `key={update.timestamp}` and a CSS class (`flash-up`/`flash-down`) from `direction`; a CSS `@keyframes` fade (~500 ms) restarts on each new key. No `setTimeout`/cleanup logic.

### Key Data Flows

1. **Price path:** source task -> `PriceCache.update` (version++) -> `stream.py` batch (once per key) -> SSE -> price store -> components. Watchlist membership comes from REST; prices are joined by ticker on the client. `GET /api/watchlist` also returns last prices (per PLAN) for first paint; `price: null` means "no data yet" (new ticker waiting for the next Massive poll).
2. **Watchlist change:** `POST/DELETE /api/watchlist` -> `services.watchlist` -> repo write -> `tracking.sync` -> response with the updated list. Client replaces its list; the SSE batch drops or adds the ticker on its own (this is the fix for the "removed tickers silently dropped" gap).
3. **Snapshot path:** `snapshot_loop` (30 s, started in lifespan, cancelled on shutdown like the source task) and `execute_trade` both call `record_snapshot`; `GET /api/portfolio/history` serves them (cap the query at the last ~2000 rows). Positions with no cache price are valued at avg_cost so a missing quote never crashes the snapshot.
4. **Chat path:** `POST /api/chat` -> `services.chat.handle_chat`: (a) build context = `build_portfolio` + watchlist with live prices + recent trades with outcomes + last N `chat_messages`; (b) `await call_llm(...)` using `litellm.acompletion` (async only; see anti-patterns); (c) validate into the `LLMReply` Pydantic model, on parse failure return a message-only reply instead of a 500; (d) for each trade call `execute_trade`, for each watchlist change call `services.watchlist`, catching `TradeError` into an `actions` entry `{type, ..., status:"error", detail}`; (e) persist user + assistant rows (assistant `actions` JSON); (f) return `{message, actions}`. Frontend then calls `portfolio.load()` once (chat may have changed anything) and renders actions inline. `LLM_MOCK=true` is a branch inside `call_llm` returning a canned `LLMReply` keyed off simple message content, so everything downstream (parsing, execution, persistence) runs for real in E2E.
5. **Trade review ("review my trades"):** no new endpoint. The context builder already includes trades + outcomes; the system prompt tells the coach to critique them in beginner language.
6. **Startup:** `connect` -> `init_db` (create tables; seed profile; seed 10 watchlist rows ONLY when the profile row was just inserted, so a user who deleted tickers does not get them back on restart) -> `tracked_tickers` -> `start_market_source` (Pattern 5) -> `Context` -> start `snapshot_loop` -> serve.

### API contract additions to PLAN.md section 8 (freeze before frontend work)

| Method | Path | Notes |
|--------|------|-------|
| GET | `/api/portfolio/trades` | NEW: trade history incl. `realized_pnl` (feeds blotter, chart markers) |
| POST | `/api/portfolio/trade` | Response is `{trade, feedback, portfolio, snapshot}`; errors are 400 `{detail}` |
| GET | `/api/portfolio` | adds `realized_pnl`; positions give qty, avg_cost, last price used |
| GET | `/api/health` | keep `{"status":"ok"}`, optionally add `source`/`stale` for ops |
| SSE | `/api/stream/prices` | batched envelope above (breaking change to current per-ticker events; update `scripts/watch_prices.py` and `test_stream.py` together) |

### Chart markers (frontend detail with an integration constraint)

Main chart series = `history[ticker]` (since page load, per PLAN). Trade markers come from `trades` filtered by ticker, snapped to the nearest series point; trades older than the series start are skipped. P&L chart series = `snapshots`; each trade already has a snapshot at its timestamp (step 4 above), so markers sit exactly on a data point. Lightweight Charts requires strictly ascending, unique time values: convert to integer seconds and de-duplicate (the 0.5 s ticks collide at second resolution; keep the last). In Lightweight Charts v5 markers are a plugin (`createSeriesMarkers(series, markers)`), not `series.setMarkers`; verify against the installed version. Sparklines: hand-rolled inline SVG polyline (10 charts at 2 Hz does not warrant 10 canvas chart instances).

---

## Serving the Next.js static export from FastAPI

- `next.config`: `output: 'export'`, `images: { unoptimized: true }`. Build output is `frontend/out/` (`index.html`, `404.html`, `_next/...`). Source: Next.js static-export guide (fetched, updated 2026-08-09).
- Single route (`app/page.tsx` only) means no SPA fallback is needed: Starlette `StaticFiles(directory, html=True)` serves `/` as `index.html` and `/_next/...` assets directly. Do not add client-side routes; keep everything on one page (panels, not pages). If a second route is ever added, `html=True` plus `trailingSlash: true` serves `/route/index.html`; a catch-all fallback is still unnecessary.
- Registration order matters: `include_router(...)` for every API router and the SSE router FIRST, then `app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")` LAST (a mount at `/` swallows everything registered after it). Mount only `if STATIC_DIR.exists()` so local backend dev and pytest run without a frontend build.
- Unknown `/api/...` paths will fall through to the static mount and return the 404 page; acceptable for this app.
- Docker: Stage 1 `npm ci && npm run build` -> copy `frontend/out` to `/app/static` in Stage 2; `STATIC_DIR=/app/static`, `DB_PATH=/app/db/finally.db` as `ENV`.
- Dev loop: `rewrites()` is explicitly UNSUPPORTED with `output: 'export'`, so a dev proxy via Next config will not work. Use `NEXT_PUBLIC_API_BASE` (default `""` = same origin) in `lib/api.ts` and an env-gated dev-only `CORSMiddleware` (`DEV_CORS_ORIGIN=http://localhost:3000`, never set in the container). Use port 8020 for test servers per project preference. Note `EventSource` also needs the base URL in dev.

---

## Suggested Build Order (with dependencies)

```
0 hygiene --> 1 DB layer --> 2 market-layer changes ---> 3 watchlist -------+
                                   |                  \                    |
                                   |                   -> 4 trading+portfolio+snapshots
                                   |                                       |
                           (SSE contract frozen)          5 chat (needs 3 and 4)
                                   |                                       |
                                   +------> 6 frontend (needs 2,3,4 contract; chat panel last, needs 5)
                                                       |
                                  7 Docker + static mount + scripts --> 8 E2E (needs all)
```

| # | Step | Depends on | Notes |
|---|------|-----------|-------|
| 0 | `.gitignore` db files, `.env.example`, `config.py`, `Ticker` validator in `schemas.py` | none | Trivial; do first so nothing sensitive is ever committed |
| 1 | `db/` schema + connection + seed + repos, `Context`, lifespan opens DB | 0 | Test with in-memory SQLite; includes `realized_pnl` column from day one |
| 2 | Market changes: `cache.version`; batched SSE + status envelope; `kind`/`last_ok` on sources; `start_market_source` (validate + fallback); simulator daily-% reference; `tracking.py`; lifespan uses tracked set | 1 | This changes the SSE contract, so land it BEFORE any frontend work. Update stream tests and `watch_prices.py` in the same step. The daily-% fix lives entirely inside `simulator.py` (`cache.update(prev_close=...)` already supports it) |
| 3 | Watchlist routes + service | 1, 2 | Smallest vertical slice that proves tracking sync end to end |
| 4 | `trading.py`, `portfolio.py`, `snapshots.py` (+ loop task), portfolio routes | 1, 2 | Core of the learning value. Test the invariant and edge cases (oversell, no cash, fractional, sell-to-zero removing the position, no price) |
| 5 | `llm.py`, `chat.py`, chat route, mock mode | 3, 4 | Reuses `execute_trade` and the watchlist service; build mock first, real call second |
| 6 | Frontend: scaffold + stores + SSE hook first, then Header/Watchlist/Sparklines, TradeBar/Positions, charts + markers, Heatmap, Blotter, Chat panel, jargon tooltips | 2 to 4 contract; 5 for chat panel | Can start in parallel with step 5 once the step 2 to 4 shapes are frozen |
| 7 | Static mount, multi-stage Dockerfile, start/stop scripts | 6 | Strongly recommended: do a walking-skeleton Docker build (placeholder `index.html`) right after step 1 or 2 to expose Windows/`uv --locked`/volume issues early, then swap in the real export |
| 8 | Playwright E2E with `LLM_MOCK=true` | all | |

Phases suggested for the roadmap: (A) persistence + tracking + market fixes (steps 0 to 2), (B) watchlist + trading + portfolio API (3, 4), (C) frontend core (6, without chat), (D) AI chat + coach (5 + chat panel), (E) packaging + E2E (7, 8). A Docker skeleton task belongs in phase A.

---

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 1 user (the actual target) | Everything above. One uvicorn worker is REQUIRED (one cache, one source, one poller) |
| A few browser tabs | Fine: batch is built once per version, per-client cost is a string send |
| Multi-user | Out of scope; `user_id` columns exist. Would need per-user context, auth, and moving the poller out of process |

### Scaling Priorities

1. **First real limit:** Massive free-tier call budget (5/min), not CPU. Do not add any extra Massive calls (no per-ticker lookups, no re-validation probes).
2. **Second:** `portfolio_snapshots` growth (2880 rows/day). Cap history reads; add pruning/downsampling only if the table gets visibly slow.

---

## Anti-Patterns

### Anti-Pattern 1: Blocking LLM call on the event loop
**What people do:** call `litellm.completion(...)` (sync) from an `async def` chat route.
**Why it's wrong:** the free Nemotron model can take many seconds; the simulator task, SSE stream and snapshot loop all freeze and the UI shows a dead connection.
**Do this instead:** `await litellm.acompletion(...)` only, with a request timeout.

### Anti-Pattern 2: Two trade code paths
**What people do:** validate in the REST route, re-implement a lighter check inside chat.
**Why it's wrong:** the AI can then overspend or oversell; behaviors diverge.
**Do this instead:** both call `services.trading.execute_trade`; chat only translates `TradeError` into an action entry.

### Anti-Pattern 3: Plain `def` routes or awaits inside the trade critical section
**What people do:** `def` handlers (threadpool) or `await` between price read and write.
**Why it's wrong:** breaks the single-thread atomicity that makes one shared sqlite connection safe; races on cash and positions.
**Do this instead:** `async def` routes, sync repos, no await before commit.

### Anti-Pattern 4: Per-client payload building and per-ticker diffs in SSE
**What people do:** keep a `last_sent` dict per connection, serialise per client.
**Why it's wrong:** unbounded state, removed tickers vanish silently, identity-compare fragility (all in CONCERNS.md).
**Do this instead:** Pattern 4.

### Anti-Pattern 5: Static mount registered before API routers
**What people do:** `app.mount("/", StaticFiles(...))` early in `main.py`.
**Why it's wrong:** swallows `/api/*` and the SSE route.
**Do this instead:** mount last, only if the directory exists.

### Anti-Pattern 6: Removing a watchlist ticker straight from the source
**What people do:** call `source.remove_ticker` from the DELETE handler.
**Why it's wrong:** an open position loses its price (portfolio value wrong, sells impossible), and a re-add resets the simulated price.
**Do this instead:** always go through `tracking.sync`.

### Anti-Pattern 7: Mid-session source flip or silent failure
**What people do:** switch Massive to simulator on the first failed poll, or swallow errors.
**Why it's wrong:** portfolio values jump between real and fake prices; silent failure looks like a frozen market.
**Do this instead:** decide once at startup, expose `stale` and the fallback note via the SSE status, badge in the header.

### Anti-Pattern 8: Business logic in SQL helpers or in the frontend
**What people do:** compute P&L inside repo queries or only in React.
**Why it's wrong:** chat context, snapshots and tests need the same numbers.
**Do this instead:** rules in `services/`, display math in `derive.ts`, tied together by the invariant test.

---

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| Massive REST | existing `MassiveSource` via httpx; validated by its first poll | Key never logged; free tier 15 s poll; startup priming request counts toward budget |
| OpenRouter via LiteLLM | `services/llm.py` only, `acompletion`, structured output from the `LLMReply` Pydantic schema, `provider.require_parameters: true`, model per PLAN section 9 | Follow the openrouter-inference skill when writing it; mock branch for `LLM_MOCK=true` |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| routes <-> services | direct calls with `ctx` | Services raise `TradeError`; routes map to 400 |
| services <-> db repos | direct calls with `ctx.db` | Repos never commit across services; `execute_trade` owns its transaction |
| services <-> market | `ctx.cache` reads, `ctx.source` via `tracking.sync` only | Only `tracking.py` calls `add_ticker`/`remove_ticker` |
| backend <-> frontend | REST JSON + one SSE stream, same origin | Contract frozen after steps 2 to 4 |
| chat <-> trading/watchlist | same service functions as manual routes | Single validation path |

---

## Open Questions / Verify During Implementation

- `fastapi.sse.ServerSentEvent` API for pre-serialised data (very new FastAPI release; existing code uses `data=` with a dict). MEDIUM.
- Lightweight Charts version and markers API (v5 plugin style) and its strict-ascending-time rule. MEDIUM (library knowledge, not re-checked this session).
- Whether to reject trades while Massive data is `stale` (recommended: yes) and the buy-outcome simplification after partial sells: product decisions for requirements.
- Real Massive snapshot shape has never been exercised with a live key (CONCERNS.md); the startup validation relies on `parse_snapshot` returning at least one ticker, so record a real response fixture when a key is available.

## Sources

- `D:/Projects - AI Coder/Day14/finally/backend/app/main.py`, `backend/app/market/{cache,stream,factory,massive,simulator,interface,models}.py` (read this session, HIGH)
- `D:/Projects - AI Coder/Day14/finally/.planning/codebase/ARCHITECTURE.md`, `CONCERNS.md`, `.planning/PROJECT.md`, `planning/PLAN.md` (HIGH)
- Next.js static exports guide, https://nextjs.org/docs/app/guides/static-exports (fetched, lastUpdated 2026-08-09; HIGH): `output: 'export'`, `out/` layout, rewrites/redirects/headers unsupported
- Starlette `StaticFiles(html=True)`, SQLite single-connection/WAL behavior, zustand selector behavior, Lightweight Charts conventions: author knowledge, MEDIUM (not re-verified via Context7, which required authentication in this session)

---
*Architecture research for: AI-assisted trading-practice workstation (FinAlly)*
*Researched: 2026-10-19*
