# Project Research Summary

**Project:** FinAlly (Finance Ally)
**Domain:** Trading-practice workstation for complete beginners (single user, single Docker container, simulated $10,000 portfolio, AI coach)
**Researched:** 2026-10-19
**Confidence:** MEDIUM-HIGH

## Executive Summary

FinAlly is a narrow, teaching-first paper-trading app: market orders only, equities only, line/area chart instead of candles, and an AI coach that explains and executes trades when asked. Experts build this with one pure, well-tested trade engine, and every trade shows its outcome right away (cash change, new average cost, realized and unrealized P&L). That is the differentiator. The stack is fixed by PLAN.md (FastAPI + uv, Next.js static export, SQLite, SSE, LiteLLM to OpenRouter). Research adds current versions: Next.js 16.4, Tailwind 4.3 (CSS-first), Lightweight Charts 5.2 (markers are a plugin), zustand for the stream-fed store, stdlib `sqlite3`.

Recommended approach: one FastAPI process (one uvicorn worker) with thin routes, services that own all rules (trade execution, portfolio, watchlist tracking, chat), and plain SQL repositories. The manual trade bar and the chat path call the same `execute_trade`. Market data stays as is, plus: a version counter on the price cache, a batched SSE envelope carrying market status, a Massive startup probe that falls back to the simulator with a visible reason, and a tracked-ticker reconciler (watchlist union open positions). The frontend derives live P&L from REST state times live prices.

Main risks: (1) the Massive free plan has no snapshot endpoint and only end-of-day data, so a free key 403s on the current poller and the app would show empty prices while claiming LIVE; (2) money and atomicity bugs (float drift, dust positions, lost realized P&L, racing manual and chat trades); (3) free-tier LLM limits and unreliable structured output; (4) frontend correctness at 2 Hz (EventSource states, re-render cost, Lightweight Charts time-order rules).

## Key Findings

### Recommended Stack

Frontend: Next.js 16.4.2 (App Router, `output: 'export'`, one page), React 19.3, TypeScript 6.0.x, Tailwind 4.3.3 (`@import "tailwindcss"` plus `@theme`, no tailwind.config.js), lightweight-charts 5.2.1 for main and P&L charts, zustand 5.0.x for the stream store, inline SVG sparklines, d3-hierarchy `treemap()` rendered as absolutely positioned divs. Tests: Vitest 5 + jsdom + React Testing Library. E2E: `@playwright/test` 1.64.1 pinned to `mcr.microsoft.com/playwright:v1.64.1-noble`.

Backend additions: `uv add litellm pydantic` (LiteLLM 1.106.0). Persistence: stdlib `sqlite3`, plain SQL, no ORM.

Docker: build stage `node:24-slim` (Node 20 EOL 2026-04-30; Next 16 needs >=20.9); runtime `python:3.12-slim`.

LLM request shape (verified against a capture server, not live): `acompletion(model="openrouter/nvidia/nemotron-3-super-120b-a12b:free", messages, response_format=ChatReply, extra_body={"provider": {"require_parameters": True}})`.

### Expected Features

**Must have (P1):** $10,000 cash; watchlist with live prices and flash; market buy/sell with instant fill and server validation (no shorting, fractional allowed); positions table (qty, avg cost, price, unrealized $ and %, weight); header (total value, cash, unrealized, realized, total P&L); connection dot and LIVE/SIMULATED badge with stale state; trade history and clear rejection messages; persistence; main price chart and P&L chart; watchlist add/remove with validation.

**Differentiators (P1 for this product):** buy/sell markers on main and P&L charts; realized and unrealized shown separately and live; blotter with "outcome so far" per trade; instant feedback card (cash before/after, average cost before/after, weight, realized on sells) shared by manual and chat trades; jargon tooltips from one glossary; AI coach that explains with the user's numbers; "review my trades" on request only, outcomes computed by the backend; treemap heatmap (size = weight, color = unrealized %, clamped about +/-5%); chat actions rendered from the `actions` array.

**Defer:** reset portfolio (v1.x, the only justified confirm dialog); day P&L per position (v1.x); persisted price history for markers (v1.x; in-window markers only in v1); alerts, CSV, multi-account, candles/indicators (v2 or out of scope).

**Anti-features:** limit/stop orders, shorting, margin, options, fees or slippage, proactive AI comments, rule-based hints, trade confirmation dialogs, tax lots, token streaming, leaderboards, news feeds.

**Accounting (one spec, feeds tests):** weighted average cost, long only, no fees. Buy: `a' = (a*q + x*n)/(q+n)`. Sell: `realized = (x - a)*n`, average unchanged. Closed position deletes the row. Invariant: `realized_total + unrealized_total == total_value - 10000`. Weight uses total value including cash. Worked example (buy 10 @190, buy 10 @200, mark 205, sell 5 @210 => avg 195, realized +75, unrealized +150, total 10,225) is the first unit test.

### Architecture Approach

`main.py` is the composition root (lifespan, include routers, static mount last). Layers: thin `routes/` (parse, call one service, map `TradeError` to 400), `services/` (all rules), `db/` repositories (SQL only). `market/` imports nothing from `db/` or `services/`. A frozen `Context(db_path, cache, source, market_note)` is built in lifespan.

Flows: trade (validate price and staleness, validate cash or shares, one transaction for cash, position, trade row with `realized_pnl`, then snapshot, feedback, tracking sync); chat (build context, `await acompletion`, parse `LLMReply`, execute actions through the same services, persist, return `{message, actions}`); price (source writes cache with version bump; stream builds one batched payload per version).

Decisions: store `realized_pnl` on sell rows (NULL for buys); buy-row outcome and unrealized derived live, never stored; client derives live numbers in `lib/derive.ts`, server authoritative at rest; portfolio refetched on mount, after trade, after chat reply, never per tick; `tracking.sync` is the only caller of `add_ticker`/`remove_ticker`; batched SSE event `{prices: [...full snapshot...], status: {source, stale, note}}` rebuilt only when `(cache.version, stale)` changes; Massive decided once at startup, no mid-session flip; `StaticFiles(html=True)` mounted last, only if the directory exists.

**SQLite access (conflict resolved):** short-lived `sqlite3.connect` per service call, `BEGIN IMMEDIATE` around every trade, busy_timeout and foreign_keys per connection, sync repos, `async def` routes calling services directly, `await` only for the LLM call (outside any transaction). Chosen over a single shared connection because the shared-connection "no await inside a trade" rule silently breaks if a `def` route or an await is ever added.

**Components:** (1) context/config; (2) `backend/app/db/` (schema.sql, connection with init and seed, repo per table); (3) trading, portfolio, watchlist, tracking, snapshots services; (4) chat and llm services (LLM_MOCK branch); (5) market (existing plus version, batched stream, kind/last_ok, `start_market_source` probe, simulator session day-% reference); (6) frontend stores, `lib/derive.ts`, `usePriceStream`, panel components.

**Deviations from PLAN.md:** DB code in `backend/app/db/` (not `backend/db/`, avoids collision with the `/app/db` volume); `trades.realized_pnl` column; `GET /api/portfolio/trades` endpoint; trade response and SSE envelope shapes changed; Node 24 build stage.

### Critical Pitfalls

1. **Massive free plan has no snapshot endpoint and only end-of-day data.** Current poller 403s on every poll, logs a warning, UI shows empty rows while claiming LIVE. Prevention: startup probe on the polling endpoint with `tickers=AAPL` (1-2 calls, 3-5 s timeout). Any non-ok (not entitled, bad key, throttled, unreachable, empty body) falls back to simulator; reason string (never the key) goes to `/api/health` and SSE status and the header. Do not start `MassiveSource` before the probe passes.
2. **Non-atomic trades and races** (manual vs chat, double-click, snapshot mid-trade). Prevention: `execute_trade` in one `BEGIN IMMEDIATE` transaction; price read from cache inside it; reject if missing or stale; chat turns serialized with an asyncio lock; snapshots value missing prices at average cost.
3. **Float money and dust.** Prevention: pure Decimal engine (cash to cents, quantity to 6 decimals, ROUND_HALF_EVEN), stored as REAL; delete position below 1e-6; `realized_pnl` on sells. Property test: random trades keep the invariant within one cent. Write these tests first.
4. **LLM output best-effort; free model rate-limited** (50/day on low-credit free key; `require_parameters` can yield "no endpoints found"). Prevention: `await acompletion` with about 60 s timeout; layered parsing (validate, strip fences, one retry on validation failure only, then plain-text reply with no actions); `max_tokens` at least 2000; no auto-retry on 429; `LLM_MOCK=true` for all automated tests and E2E. Guardrails in server path: max about 5 trades per message, reject duplicate (ticker, side), require valid ticker with price, quantity > 0; user text in user role only.
5. **EventSource and SSE delivery.** Non-200 or wrong content type on reconnect makes EventSource stop (CLOSED). Prevention: `usePriceStream` maps onopen to green, CONNECTING to yellow, CLOSED to red with manual re-create on backoff (1, 2, 5 s); `close()` in cleanup (Strict Mode); no GZip middleware; one worker; `--timeout-graceful-shutdown 2`; API routers before static mount; unknown `/api/*` returns JSON 404.
6. **Frontend performance and Lightweight Charts rules.** Prevention: zustand selectors per row; flash via CSS class keyed by timestamp; integer-second times, overwrite last point when second unchanged; markers snapped to existing bar times and rebuilt on trade events only; one main chart instance, SVG sparklines; capped history and capped `/api/portfolio/history`.

Also carry: Next export config (`output: 'export'`, `trailingSlash: true`, `images.unoptimized`, no rewrites, relative `/api`, `NEXT_PUBLIC_API_BASE` for dev only); SQLite on Docker (named volume only, gitignore `db/*.db*`); script portability (`.gitattributes`, `MSYS_NO_PATHCONV=1`, `-ExecutionPolicy Bypass`, `docker info` check, publish `127.0.0.1:8000:8000`, rate limit `/api/chat`); Day % true previous close on Massive, session reference in simulator labelled as such; never log secrets; `.env` only via Docker `--env-file`, unquoted values.

## Implications for Roadmap

### Phase 1: Foundation, market hardening, walking-skeleton Docker

**Rationale:** Everything needs the DB, tracked-ticker set, and frozen SSE contract; Massive decision must precede price-dependent UI.
**Delivers:** `backend/app/db/` (schema with `realized_pnl`, `CREATE TABLE IF NOT EXISTS`, seed in lifespan only on new profile, foreign_keys, busy_timeout); config; Ticker validator (`^[A-Z]{1,5}(\.[A-Z])?$`); Context; `cache.version`; batched SSE with status; `kind`/`last_ok`; `start_market_source` probe and fallback with reason; simulator session day-% reference; `tracking.py`; watchlist routes and service; `.gitignore`, `.env.example`; `/api/health` with source and reason; updated `watch_prices.py` and stream tests; walking-skeleton Dockerfile.
**Addresses:** starting cash, persistence, live watchlist, status badge, watchlist validation.
**Avoids:** Pitfalls 1, 2, 3, 14, 16, 17, 18, 26.

### Phase 2: Trade engine, portfolio, snapshots

**Rationale:** Keystone for manual trades, chat trades, blotter, feedback, markers, P&L chart.
**Delivers:** `services/trading.py` (`execute_trade`, `TradeError`, Decimal engine, `BEGIN IMMEDIATE`, stale and missing-price rejection); `services/portfolio.py`; `GET /api/portfolio`, `POST /api/portfolio/trade` (returns `{trade, feedback, portfolio, snapshot}`), `GET /api/portfolio/trades`, `GET /api/portfolio/history` (capped); `services/snapshots.py` (30 s loop plus after each trade; missing prices at average cost); invariant tests; concurrency test (parallel trades never overdraft).
**Avoids:** Pitfalls 4, 5, 17.

### Phase 3: Frontend core (no chat)

**Rationale:** Builds on frozen phase 1 and 2 contracts; charts and marker rules are the riskiest frontend work, so after stores and stream hook.
**Delivers:** Next.js scaffold (export config, Tailwind 4 theme, Vitest); `store/prices.ts`; `store/portfolio.ts`; `usePriceStream`; `lib/derive.ts` with invariant tests; Header (totals, dot, LIVE/SIMULATED badge with reason); Watchlist (flash, sparklines, add/remove); TradeBar; PositionsTable; Blotter; feedback card; main chart with markers; P&L chart with markers; treemap; `Term` tooltips from one glossary.
**Avoids:** Pitfalls 10, 12, 13, 16, 25, 3.

### Phase 4: AI coach and chat

**Rationale:** Depends on phases 1 and 2. Mock-first so downstream paths run for real in tests.
**Delivers:** `services/llm.py` (`acompletion`, `require_parameters`, Pydantic `LLMReply`, `LLM_MOCK` branch keyed on simple text: reply, buy, sell, watchlist add, failing trade, malformed); `services/chat.py` (context with live prices, outcomes, last N messages; guardrails; persist user and assistant rows with `actions` JSON; request id for idempotency); `POST /api/chat`; chat panel (inline action cards, loading state, input disabled in flight); "review my trades" via same endpoint; simple in-memory rate limit on `/api/chat`.
**Avoids:** Pitfalls 6, 7, 8, 9, 21, 22.

### Phase 5: Packaging, scripts, E2E

**Rationale:** Needs all features; walking skeleton already proved the build.
**Delivers:** full multi-stage Dockerfile (`node:24-slim`, `python:3.12-slim` with `uv sync --locked`, STATIC_DIR and DB_PATH ENV, one worker, graceful shutdown timeout); static mount last; `.dockerignore`; idempotent start and stop scripts (Docker check, Python healthcheck, 127.0.0.1 port, optional browser); `.gitattributes`; `test/` with Playwright, `docker-compose.test.yml` (`LLM_MOCK=true`, service-name baseURL, healthcheck, shm_size, ephemeral DB); E2E scenarios from PLAN.md section 12 plus SSE restart recovery; `curl -N` cadence check on the running container.
**Avoids:** Pitfalls 11, 12, 14, 15, 20, 22.

### Phase Ordering Rationale

- DB and tracking before trades; SSE contract frozen before frontend depends on it.
- Trade engine before both trade bar and chat, since it is the single path.
- Frontend can start once phase 1 and 2 shapes are fixed; chat is last feature; packaging and E2E last.

### Research Flags

**Needs research or live spike:** Phase 1 (live Massive responses for ok, 403, 401/403, 429, timeout; `fastapi.sse` raw-data API); Phase 3 (LWC 5.2 marker behaviour with off-grid times and same-second updates; attribution requirement); Phase 4 (live Nemotron smoke test: `response_format` plus `require_parameters` routing, LiteLLM `$defs`/`$ref`, empty content, latency).

**Standard patterns:** Phase 2 (pure accounting, test-first); Phase 5 (standard multi-stage build; verify scripts on Windows and macOS); Phase 3 shell (official Next export and Tailwind v4 docs).

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH (versions), MEDIUM (runtime behaviour) | Versions from npm and PyPI 2026-10-19; Next export and Tailwind v4 from official docs; LWC marker rules, NVIDIA `$ref` handling, reasoning tokens from memory or inference |
| Features | MEDIUM | Accounting HIGH (broker docs); Investopedia and Webull rows LOW-MEDIUM; UX choices are synthesis |
| Architecture | HIGH | Grounded in existing code; verify `fastapi.sse` raw-data API and StaticFiles behaviour |
| Pitfalls | MEDIUM-HIGH | Massive plan matrix and OpenRouter limits from official pages; EventSource, SQLite pragmas, Windows scripts MEDIUM; third-party error rates LOW, not relied on |

**Overall:** MEDIUM-HIGH. Main uncertainty is external behaviour (live Massive responses per plan; live LLM endpoint); both are cheap to check early.

### Gaps to Address

- **Massive live behaviour (no key during research):** invalid key vs not entitled vs throttled codes not precisely documented. Phase 1 probe classifies by status and exception without assuming 401; capture a real fixture once a key is available; any non-ok falls back safely.
- **Market-closed and 3:30 AM ET reset:** treat frozen prices as LIVE (not stale); show "as of" timestamps; verify empirically.
- **Free Nemotron structured output:** live smoke test in phase 4; plain-text fallback built in; `LLM_MOCK` covers automated tests.
- **LWC marker details:** spike in phase 3; rule (integer seconds, dedupe, snap to bars) is conservative either way.
- **`fastapi.sse` pre-serialised payload:** if unavailable, re-serialise per client (cheap at 5 tabs); do not block phase 1.
- **Buy outcome after partial sells:** label "(partly sold)"; keep simplification documented in tooltip.
- **Product decisions to confirm:** reject trades while STALE (recommended yes); reset button in v1 or v1.x (recommended v1.x); cap of about 5 trades per chat message and per-trade notional cap.
- **Simulator day-%:** session-start based unless persisted; label "since session start" in simulated mode.

## Sources

**Primary (HIGH):** Next.js static exports guide (2026-08-09); Next.js TypeScript config docs (2026-08-25); Tailwind v4 Next.js install guide; Lightweight Charts v4-to-v5 migration and `createSeriesMarkers` docs; Massive pricing page and snapshot, previous-day, grouped-daily, custom-bars docs; OpenRouter limits and structured-outputs docs; OpenRouter models API (Nemotron free endpoint); FastAPI SSE tutorial; npm and PyPI registries (2026-10-19); Node.js release schedule; existing code `backend/app/main.py`, `backend/app/market/*`, `.planning/codebase/ARCHITECTURE.md`, `CONCERNS.md`, `.planning/PROJECT.md`, `planning/PLAN.md`.

**Secondary (MEDIUM):** LiteLLM 1.106.0 capture-server experiment (request body shape; not live); Moomoo, Vanguard, Portfolio Performance cost-method docs; TradingView paper trading help; thinkorswim paperMoney page.

**Tertiary (LOW, validate):** Investopedia and Webull feature rows (general knowledge, verify before quoting); third-party Nemotron free-endpoint directories (unverified, not relied on); Simon Willison asgi-gzip post (April 2026); Docker forum SQLite-on-Windows thread (2016); EventSource, SQLite pragma scope, Chrome connection limits, MSYS path conversion, Docker `--env-file` quoting, PowerShell execution policy (established, not re-verified).

---
*Research completed: 2026-10-19*
*Ready for roadmap: yes*
