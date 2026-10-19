---
last_mapped_commit: 24a4b2a30df1d0f61a24990f210bc270e83cd728
last_mapped_at: 2026-10-19
---
# Codebase Concerns

**Analysis Date:** 2026-10-19

## Scope Note

Only the market data layer exists in code (`backend/app/main.py`, `backend/app/market/*`, `backend/scripts/watch_prices.py`, `backend/tests/market/*`). The rest of `planning/PLAN.md` (portfolio, trades, watchlist routes, chat/LLM, SQLite, frontend, Dockerfile, start/stop scripts, E2E tests) is not implemented. Concerns below are limited to what exists, plus gaps that block the planned features.

Verified state: `cd backend && uv run pytest -q` passes 54 tests (run on 2026-10-19).

## Tech Debt

**Watchlist and open positions not wired into market tracking:**
- Issue: The lifespan hard-codes `DEFAULT_TICKERS` as the tracked set. The TODO says it must become "watchlist UNION open positions from SQLite".
- Files: `backend/app/main.py` (line 14 TODO, line 22 `source.start(DEFAULT_TICKERS)`), `backend/app/market/seed_data.py`
- Impact: Tickers added to the watchlist later are not priced unless something calls `app.state.market_source.add_ticker()`. No code path does this yet. Open positions in tickers outside the default 10 would have no price.
- Fix approach: When the database layer lands, load the union from SQLite in the lifespan, and call `add_ticker` / `remove_ticker` from the watchlist and trade routes. Keep `MarketDataSource` as the only entry point.

**Simulator "Day %" is cumulative from seed, not a daily change:**
- Issue: `SimulatorSource._seed` sets `prev_close = seed price` and never updates it. `PriceUpdate.change_pct` is therefore the change since process start, labelled as day change in the watch script and in PLAN.md's "daily change %".
- Files: `backend/app/market/simulator.py` (`_seed`, `step`), `backend/app/market/models.py` (`change_pct`), `backend/scripts/watch_prices.py` (column "Day %")
- Impact: Users see "daily" change that resets on every restart and drifts with the random walk. Massive mode uses real `prevDay` closes, so the two modes behave differently.
- Fix approach: Either rename the field to "since start" in the simulator path, or have the simulator keep a simulated session open/close that rolls over on a schedule. Document the choice in `planning/MARKET_DATA_DESIGN.md`.

**Global module-level app and state:**
- Issue: `app = FastAPI(lifespan=lifespan)` is created at import time, and `PriceCache` is created inside lifespan but stored on `app.state`. The stream route reads `request.app.state.price_cache`.
- Files: `backend/app/main.py`, `backend/app/market/stream.py` (`stream_prices`)
- Impact: Tests must use the lifespan context manager (see `backend/tests/market/test_app.py`). Adding routes that need the cache or source before the lifespan runs will raise `AttributeError` on `app.state`.
- Fix approach: Keep the pattern, but add a small dependency helper (e.g. `get_cache(request)`) when more routes need shared state, so the attribute access lives in one place.

**Unbounded per-connection state in SSE stream:**
- Issue: `price_events` keeps `last_sent` for every ticker ever seen on that connection. Tickers removed from the cache are never pruned from `last_sent`.
- Files: `backend/app/market/stream.py` (`price_events`)
- Impact: Small memory growth per long-lived connection as the watchlist churns. Negligible at 10 tickers, but it is unbounded in principle.
- Fix approach: Rebuild `last_sent` from `cache.all()` each loop, or drop keys whose ticker is no longer in the cache.

**Duplicated cache-write logic in both sources:**
- Issue: `start`, `stop`, and the `_task` lifecycle are copy-pasted in `SimulatorSource` and `MassiveSource`.
- Files: `backend/app/market/simulator.py` (lines 40-53), `backend/app/market/massive.py` (lines 55-72)
- Impact: Future fixes (e.g. cancellation handling) must be applied twice.
- Fix approach: Move the task start/stop into a small base helper in `interface.py`, only if a third source is added. Otherwise leave as is.

## Known Bugs and Behavioural Gaps

**Removed tickers are silently dropped from the stream:**
- Symptoms: After `remove_ticker`, the SSE stream sends nothing for that ticker. Clients keep showing the last price.
- Files: `backend/app/market/stream.py`, `backend/app/market/cache.py` (`remove`)
- Trigger: Any call to `remove_ticker` while a client is connected.
- Workaround: Frontend must re-read `GET /api/watchlist` after add/remove (planned, not built). Documented in `planning/MARKET_DATA_REVIEW.md` (L3) and `planning/MARKET_DATA_DESIGN.md` section 10.

**Re-adding a ticker resets its simulated price:**
- Symptoms: Remove `AAPL` at 197.00, add it back, price jumps to the seed 190.00.
- Files: `backend/app/market/simulator.py` (`add_ticker`, `_seed`)
- Trigger: Remove then re-add a watch-only ticker.
- Workaround: None. Accepted by design (`planning/MARKET_DATA_DESIGN.md` section 9).

**Massive poll failures are silent to the user:**
- Symptoms: When Massive returns an error or is unreachable, the cache keeps stale prices and the SSE stream keeps pushing nothing new. The UI can look connected but frozen.
- Files: `backend/app/market/massive.py` (`poll_once`, lines 99-103), `backend/app/market/stream.py`
- Trigger: Invalid key, network outage, or 429 rate limit.
- Workaround: Check server logs for `Massive poll failed`. No staleness timestamp is exposed to clients. Consider adding a `stale` flag or a health field once the frontend connection indicator is built (PLAN.md section 10 requires a status dot).

**Watch script does not reconnect:**
- Symptoms: If the server restarts or the stream drops, `scripts/watch_prices.py` raises out of `iter_lines` and exits with a traceback.
- Files: `backend/scripts/watch_prices.py` (`main`, lines 117-126)
- Trigger: Stop and restart uvicorn while the watcher runs.
- Workaround: Restart the script. Acceptable for a developer tool, but `EventSource`-style retry is not implemented here.

## Security Considerations

**Database file not git-ignored:**
- Risk: The planned SQLite file `db/finally.db` (PLAN.md section 7) is not covered by `.gitignore`. `.gitignore` only lists `db.sqlite3` and `db.sqlite3-journal`. The file would be committed with trade history and any user data on first run.
- Files: `.gitignore`
- Current mitigation: None. `db/` directory does not exist yet.
- Recommendations: Add `db/finally.db`, `db/finally.db-journal`, and `db/*.db` to `.gitignore` before the database step, and keep `db/.gitkeep` tracked as PLAN.md requires.

**Secrets handling is convention only:**
- Risk: `MASSIVE_API_KEY` (and later `OPENROUTER_API_KEY`) are read from the process environment. `backend/README.md` tells developers to run `uv run --env-file ../.env`. Nothing prevents a key from being logged or echoed.
- Files: `backend/app/market/factory.py` (line 11), `backend/app/market/massive.py` (client header, line 42), `backend/README.md`
- Current mitigation: The key is only sent as a Bearer header to `https://api.massive.com`. `.env` is listed in `.gitignore` (line 138). The Massive client does not log request headers. `.env.example` is referenced in `README.md` but is not present in the repository.
- Recommendations: Add a committed `.env.example` with empty values (this is what the root README and PLAN.md describe). Avoid logging `exc` from `httpx` in full if it can include request URLs with query params (the tickers list is not sensitive, but keep it that way).

**No input validation on tickers yet:**
- Risk: `MarketDataSource` docs say "the API layer normalizes" tickers to upper case. No API layer exists yet. Unvalidated ticker strings would be sent to Massive in the `tickers` query parameter (`backend/app/market/massive.py`, line 88) and used as cache keys.
- Files: `backend/app/market/massive.py`, `backend/app/market/simulator.py` (`add_ticker`)
- Current mitigation: Only the lifespan passes tickers in, and those are hard-coded.
- Recommendations: When the watchlist POST route is added, validate with a regex (e.g. `^[A-Z.]{1,10}$`) and reject anything else before it reaches a source.

**No authentication or rate limiting on the planned API:**
- Risk: PLAN.md has no login. Trade and chat endpoints will be open to anyone who can reach port 8000. Chat calls cost money against the OpenRouter key.
- Files: Not yet implemented (`backend/app/main.py` has only `/api/health` and the SSE route)
- Current mitigation: Single-user local app by design (PLAN.md section 1).
- Recommendations: Keep the app bound to `127.0.0.1` in the start scripts, and add a simple per-IP limit on `POST /api/chat` before deploying anywhere public.

## Performance Bottlenecks

**Every SSE client re-scans the full cache every 0.5 s:**
- Problem: `price_events` loops over `cache.all()` (which builds a new list) for every connected client, every 0.5 s, and serialises each changed ticker separately.
- Files: `backend/app/market/stream.py` (`price_events`), `backend/app/market/cache.py` (`all`)
- Cause: Per-client work is O(tickers) with no batching. The simulator changes all tickers on every tick, so each client gets about 20 events per second for 10 tickers.
- Improvement path: Fine at this scale. If the watchlist grows, send one batched event per tick (a JSON list) instead of one event per ticker, and build the payload once per tick rather than once per client.

**Simulator tick is synchronous and runs on the event loop:**
- Problem: `SimulatorSource.step` loops over every ticker with `math.exp` and `rng.gauss` calls inside the asyncio task.
- Files: `backend/app/market/simulator.py` (`step`, `_run`)
- Cause: Pure Python per tick. Cost grows linearly with tracked tickers.
- Improvement path: No action needed at 10 tickers. Measure before changing if the watchlist exceeds a few hundred entries.

**Massive start blocks app startup:**
- Problem: `MassiveSource.start` awaits the first poll before the server accepts requests. A slow Massive response delays startup by up to the 10 s client timeout.
- Files: `backend/app/market/massive.py` (`start`, line 61), `backend/app/market/factory.py`
- Cause: Deliberate, so the first SSE push has data (`planning/MARKET_DATA_REVIEW.md` L5).
- Improvement path: Accepted trade-off. Could move the priming poll into the background task if startup time becomes a problem.

## Fragile Areas

**Massive rate limit depends on an env var with no bounds:**
- Files: `backend/app/market/factory.py` (line 13), `backend/app/market/massive.py`
- Why fragile: `MASSIVE_POLL_SECONDS` is parsed with `float(...)` and has no minimum. The free Massive tier allows 5 calls per minute (PLAN.md section 6). Setting it below 12 s gets HTTP 429 responses, which are logged as warnings and not retried or backed off. A non-numeric value crashes startup with `ValueError`.
- Safe modification: Keep the default at 15 s. If the variable is changed, check the tier first. Consider clamping to a minimum and validating at startup.
- Test coverage: `backend/tests/market/test_factory.py` checks that the value is read, not that bad values are rejected. No test covers 429 handling.

**Massive response parsing is tied to one undocumented shape:**
- Files: `backend/app/market/massive.py` (`parse_snapshot`, lines 14-30)
- Why fragile: Field names (`lastTrade.p`, `min.c`, `day.c`, `prevDay.c`, `ticker`) are hard-coded. Tests use mocked payloads written by the same author, so a real API change would not be caught until a live key is used.
- Safe modification: Add one recorded real response as a fixture when a live key is available. The review notes that no live call has been made (`planning/MARKET_DATA_REVIEW.md`, "Still open").
- Test coverage: 13 tests in `backend/tests/market/test_massive.py` use `httpx.MockTransport`. None hit the real API.

**Stream reliance on object identity for change detection:**
- Files: `backend/app/market/stream.py` (line 25), `backend/app/market/cache.py` (`update`)
- Why fragile: A ticker is re-sent only when `cache.update` creates a new `PriceUpdate` object. Any future code that mutates or caches `PriceUpdate` objects (or reuses one) would silently stop pushes. `PriceUpdate` is a frozen dataclass, which protects against mutation but not against reuse.
- Safe modification: Do not reuse `PriceUpdate` instances across writes. If a sequence number is ever needed, add it to `PriceUpdate` rather than comparing timestamps (`planning/MARKET_DATA_REVIEW.md` L2).
- Test coverage: `backend/tests/market/test_stream.py` has `test_update_with_same_timestamp_is_still_sent`.

**Simulator random source is injectable but global by default:**
- Files: `backend/app/market/simulator.py` (`__init__`, line 35), `backend/tests/market/test_simulator.py`
- Why fragile: `random.Random()` is unseeded in production, which is correct. Statistical tests depend on injected seeds, and any change to the number or order of `rng` calls in `step` changes the expected outputs.
- Safe modification: When changing `step` or `_correlated_shock`, rerun the correlation tests (`test_simulator.py`) and expect them to fail on a seed change.

## Scaling Limits

**In-memory price cache is single-process only:**
- Current capacity: One uvicorn worker, 10 default tickers, one simulator or one Massive poller.
- Limit: Running more than one worker (`uvicorn --workers N`) creates N independent caches and N market sources. Each would call Massive separately and consume the rate limit N times.
- Scaling path: Keep one worker (as the Docker plan implies). If scaling is needed, move the poller to a separate process and share prices through SQLite or Redis.

**Massive free tier call budget:**
- Current capacity: One request per poll covering all tickers (`massive.py`, `poll_once`). At 15 s polling this is 4 requests per minute.
- Limit: 5 requests per minute on the free tier (PLAN.md section 6). Headroom is one request per minute, and any retry or restart that calls `start()` adds a priming request.
- Scaling path: Paid tiers allow 2 to 15 s polling (PLAN.md section 6). Make the interval a documented setting, and add backoff on 429.

## Dependencies at Risk

**Very new FastAPI SSE API:**
- Risk: `stream.py` imports `fastapi.sse.EventSourceResponse` and `ServerSentEvent`, which are only in recent FastAPI releases. `backend/pyproject.toml` pins `fastapi>=0.143.1`.
- Impact: Installing an older FastAPI, or a Docker build that resolves differently, fails at import time in `app/market/stream.py`.
- Migration plan: Keep the lock file (`backend/uv.lock`) committed and build the Docker image from it (`uv sync --locked`). Do not loosen the lower bound.

**`rich` in the dev group but used by a script:**
- Risk: `backend/scripts/watch_prices.py` imports `rich`, which is only in `[dependency-groups] dev` in `backend/pyproject.toml`.
- Impact: `uv sync --no-dev` (as a production image might use) removes `rich`, and the watch script fails with `ModuleNotFoundError`. The script is a developer tool, so the impact is limited.
- Migration plan: Keep it in dev and document `uv run scripts/watch_prices.py` as a dev-only command, or move `rich` to a separate `tools` group.

## Missing Critical Features

**No database layer:**
- Problem: PLAN.md sections 7 and 8 define SQLite tables, lazy initialization, and seed data (`users_profile`, `watchlist`, `positions`, `trades`, `portfolio_snapshots`, `chat_messages`). None exist. `backend/db/` (planned schema location) is absent.
- Blocks: Portfolio, trades, watchlist CRUD, P&L history, chat history, and the lifespan TODO above.

**No trading or portfolio API:**
- Problem: `POST /api/portfolio/trade`, `GET /api/portfolio`, `GET /api/portfolio/history`, `GET /api/watchlist`, `POST /api/watchlist`, `DELETE /api/watchlist/{ticker}` (PLAN.md section 8) are not implemented. Only `/api/health` and `/api/stream/prices` exist (`backend/app/main.py`, `backend/app/market/stream.py`).
- Blocks: Every user-facing feature except live prices.

**No LLM integration:**
- Problem: No LiteLLM/OpenRouter client, no structured-output schema, no `LLM_MOCK` path. `OPENROUTER_API_KEY` is read nowhere in code.
- Blocks: AI chat, auto-executed trades, and the mock mode needed for E2E tests.

**No frontend, Dockerfile, scripts, or E2E tests:**
- Problem: `frontend/`, `Dockerfile`, `docker-compose.yml`, `scripts/start_*.sh|ps1`, `scripts/stop_*`, and `test/` are absent from the repository. `README.md` describes them as "planned".
- Blocks: The single-command launch and browser-based acceptance criteria in PLAN.md.

**Market-data tests are the only test suite:**
- Problem: `backend/tests/market/` covers the market layer only. No frontend unit tests, no Playwright tests.
- Blocks: Regression safety for the features above when they are added.

## Test Coverage Gaps

**Real Massive API path:**
- What's not tested: Live HTTP calls, real response shapes, 429 responses, and timeouts against `api.massive.com`.
- Files: `backend/app/market/massive.py`, `backend/tests/market/test_massive.py`
- Risk: Parser mismatches with the real API would only show up when a user enables `MASSIVE_API_KEY`.
- Priority: High before any real-data release.

**Factory validation of bad env values:**
- What's not tested: Non-numeric or negative `MASSIVE_POLL_SECONDS`.
- Files: `backend/app/market/factory.py`, `backend/tests/market/test_factory.py`
- Risk: Startup crash with an unclear error, or a zero interval that hammers the API.
- Priority: Medium.

**Stream disconnect and cleanup under load:**
- What's not tested: Many simultaneous SSE clients, and cleanup of `last_sent` after tickers are removed.
- Files: `backend/app/market/stream.py`, `backend/tests/market/test_stream.py`
- Risk: Slow memory growth or stalled clients not detected.
- Priority: Low at current scale.

**Watch script:**
- What's not tested: `backend/scripts/watch_prices.py` has no tests. Its `TickerStats`, `sparkline`, and `pct` helpers are pure functions and easy to unit test.
- Files: `backend/scripts/watch_prices.py`
- Risk: Display bugs go unnoticed. Low impact.
- Priority: Low.

---

*Concerns audit: 2026-10-19*
