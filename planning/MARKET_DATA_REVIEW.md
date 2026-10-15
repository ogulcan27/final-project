# Market Data Backend - Code Review

Review date: 2026-10-15. Branch `week3-day2`, commit `2168c7d`.

Scope: `backend/app/main.py`, `backend/app/market/*`, `backend/tests/market/*`, checked against `PLAN.md` (sections 5, 6, 8) and `MARKET_DATA_DESIGN.md`.

## 1. Verdict

**Approve, with one fix before the Massive source is used in production.**

The market data layer is small, readable and matches the design closely. The interface, cache, simulator, factory and SSE stream are correct. The math is correct and the tests verify it statistically. The one real defect is in the Massive poller: an unexpected payload stops polling permanently and silently (finding M1). The simulator path, which is the default, has no defects.

## 2. Test Results

| Check | Result |
|---|---|
| `uv run pytest -v` | **49 passed** in 1.4s (Python 3.14.8, FastAPI 0.143.1, Starlette 1.8.0, httpx 0.28.1) |
| Repeated 5 times (flakiness check on timing-based tests) | 49 passed every run |
| Live smoke test: `uv run uvicorn app.main:app`, then `curl -N /api/stream/prices` for 2s | 200, `text/event-stream`, `retry: 1000` first, then 40 `data:` events (10 tickers x 4 pushes) |
| `GET /api/health` | `{"status":"ok"}` |

Tests per module: cache/models 10, factory 5, Massive 13, simulator 13, stream 6, app 2.

## 3. What Is Done Well

- **Clean interface.** `MarketDataSource` is a minimal ABC. Both sources implement it, and nothing downstream knows which one runs.
- **Correct GBM.** The exact discretization `S * exp((mu - sigma^2/2) dt + sigma sqrt(dt) z)` keeps prices positive. Internal prices are unrounded; only cache writes are rounded to cents, so rounding error does not accumulate.
- **Correct correlation.** The factor mix `sqrt(0.3) Z_market + sqrt(0.3) Z_sector + sqrt(0.4) eps` has unit variance. The test measures same-sector correlation at 0.6 and cross-sector at 0.3 within +-0.05, which is a strong check.
- **Testable design.** `step()` is synchronous with an injectable `random.Random`. `price_events()` was extracted from the route and takes `is_disconnected` as a callable, so the stream logic is tested without HTTP. `MassiveSource` takes an injectable `httpx.AsyncClient`, so tests use `MockTransport` and never hit the network.
- **Improvements over the design doc.** `poll_once` also catches `ValueError` (invalid JSON), and it ignores tickers that were removed while a request was in flight (`if ticker in self._tickers`). Both are tested.
- **One request per poll** for all tickers, so the watchlist size does not affect the Massive rate limit.
- Code style follows the project rules: short modules, short functions, clear names, docstrings, no emojis.

## 4. Findings

Severity: **High** = wrong behavior users will hit. **Medium** = wrong behavior in a plausible failure case. **Low** = quality or maintainability.

### M1 (Medium) - One unexpected Massive payload stops price polling forever

`massive.py:86-101`. `poll_once` catches only `httpx.HTTPError` and `ValueError`. `parse_snapshot` can raise other errors on a payload it does not expect. Any such error ends the `_run` task. There is no log message, and no restart.

Proof (script run against the current code, mocked transport, poll interval 10ms):

```
parse_snapshot({"tickers": None})                     -> TypeError
parse_snapshot({"tickers": [{"lastTrade": {"p": 1}}]}) -> KeyError   (no "ticker" key)
parse_snapshot([1, 2])                                 -> AttributeError
Second poll returns {"tickers": null}:
  calls after 0.3s: 2, task done: True, exc: TypeError
  source.stop() then re-raises the TypeError at shutdown
```

Effects:
- Prices freeze for the rest of the session. The SSE stream sends nothing more, so the UI looks connected but static.
- If the *first* poll in `start()` gets such a payload, the error propagates out of the lifespan and the app does not start.
- At shutdown, `stop()` re-raises the stored error.

Fix: in `_run`, catch and log any `Exception` from `poll_once` so the loop continues (a poll loop that talks to an external service is the one place where a broad catch is justified). Or make `parse_snapshot` tolerant (`payload.get("tickers") or []`, skip items without `"ticker"`). Add one test: a malformed payload followed by a valid one still updates the cache.

### M2 (Medium) - SSE stream has no keep-alive, so idle connections can be dropped

`stream.py:15-28`. The stream sends bytes only when a price changes. With Massive the gap is 15s between bursts, and when the market is closed or a poll fails, prices may not change for a long time (the cache is only re-stamped on a successful poll). Proxies and load balancers (App Runner, Render, nginx) commonly close connections idle for 30-60s. The client then reconnects, and the status dot flickers yellow.

Fix: FastAPI 0.143 (the installed version) has native SSE: `fastapi.sse.EventSourceResponse` with `ServerSentEvent`, and it sends keep-alive comment pings automatically. This is the latest API and would also remove the manual `f"data: {...}\n\n"` formatting. Minimal alternative: yield a `": ping\n\n"` comment every ~15s of silence.

### L1 (Low) - The drift test cannot detect a wrong drift

`test_simulator.py:107-116`. The per-tick drift is `1.24e-7`, but the tolerance (5 standard errors over 20,000 steps) is `1.41e-5`, which is 114 times larger. I re-ran the test logic with `mu = -1.0` instead of `0.08` and it still passes. The test only proves that the mean is close to zero.

Fix: either delete it (the std and correlation tests already check the math), or test the drift term directly, e.g. call `step()` with a stubbed `rng.gauss` that returns 0 and check `price == S * exp((mu - sigma^2/2) * DT)` exactly.

### L2 (Low) - Change detection compares float timestamps

`stream.py:25`. A ticker is re-sent when `update.timestamp` differs from the last one sent. Two cache writes for the same ticker inside one clock tick would look like one update. With 500ms ticks and 15s polls this does not happen today, so no fix is needed now. If update rates ever increase, use a per-update sequence number instead.

### L3 (Low) - Clients are never told that a ticker was removed

The SSE stream only sends updates. After `remove_ticker`, the ticker stops appearing, but the client keeps its last price. This is acceptable because the frontend refreshes the watchlist from `GET /api/watchlist` after add/remove. The frontend agent should be told this explicitly.

### L4 (Low) - Re-adding a known ticker resets its simulated price

`simulator.py:58-61`. Removing `AAPL` and adding it back re-seeds it at 190.00, even if the stream had moved it to, say, 197. The design already says tickers with open positions stay tracked (section 9), so this only affects watch-only tickers. It is worth knowing when the watchlist routes are built. No fix needed.

### L5 (Low) - Massive `start()` blocks startup for up to 10s

`massive.py:61-64`. The first poll is awaited inside the lifespan to prime the cache. If Massive is slow, startup waits up to the 10s client timeout. This is a reasonable trade-off (the first SSE push has data); it is noted only so nobody is surprised by a slow start.

### L6 (Low) - Small items

- `main.py:14` has a TODO: tracked tickers are `DEFAULT_TICKERS`, not "watchlist UNION open positions". This is expected until the database exists, but it must be done in the database step.
- `.env` is not loaded by the app. Docker `--env-file` covers the container, but `uv run uvicorn` locally will not see `MASSIVE_API_KEY` from `.env`. Decide this when the rest of the backend is wired (e.g. `uv run --env-file ../.env uvicorn ...`).
- Local tests ran on Python 3.14; the Dockerfile plan uses 3.12. Nothing in the code needs more than 3.12, but a `.python-version` file of `3.12` would keep local and container runs identical.
- `test_simulator.py:4-5` has a stray double blank line in the imports.
- `test_stream.py::test_route_returns_sse_response` builds a raw `Request` and checks headers only. No test streams through real HTTP. The live smoke test above covers this, but one `httpx.ASGITransport` streaming test would make it permanent.

## 5. Conformance to the Plan and Design

| Requirement | Status |
|---|---|
| One abstract interface, two implementations | Done |
| Source chosen from `MASSIVE_API_KEY` (empty or whitespace -> simulator) | Done, tested |
| GBM, ~500ms ticks, correlated moves, 2-5% random events | Done, tested |
| Realistic seed prices; unknown tickers get a random price in [50, 300] | Done, tested |
| Massive REST polling, one call per poll, configurable interval (`MASSIVE_POLL_SECONDS`, default 15) | Done, tested |
| Cache holds price, previous price, timestamp | Done (plus `prev_close` for daily change %) |
| `GET /api/stream/prices`, event has ticker, price, previous price, timestamp, direction | Done, verified live |
| `GET /api/health` | Done |
| Lifespan loads watchlist UNION positions from SQLite | Not yet (TODO; database not built) |

Documentation drift:
- `UNDERSTANDING.md` still says "The application code is not written yet." It should now say the market data layer is implemented.
- `MARKET_DATA_DESIGN.md` section 10 shows the old inline stream generator; the code now uses `price_events()`. Section 7.2 shows the old exception handling. Update both if the design doc is meant to stay in sync with the code.

## 6. Recommended Actions

In order:

1. Fix M1 (poll loop survives any error) and add a test for it.
2. Fix M2: move the SSE route to FastAPI's native `EventSourceResponse` (keep-alive included).
3. Replace or remove the drift test (L1).
4. Add one real-HTTP streaming test (L6).
5. Update `UNDERSTANDING.md` status and the stale code in `MARKET_DATA_DESIGN.md`.
6. When the database is built: replace `DEFAULT_TICKERS` in the lifespan, and implement the watchlist routes so held positions stay tracked (design section 9).
