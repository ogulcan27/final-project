---
last_mapped_commit: 24a4b2a30df1d0f61a24990f210bc270e83cd728
last_mapped_at: 2026-10-19
---
# Testing Patterns

**Analysis Date:** 2026-10-19

## Scope

Only backend unit tests exist, all for `backend/app/market/`. There are no frontend tests, no Playwright E2E tests in `test/`, and no `test/` directory yet. Tests are planned per `planning/PLAN.md` section 12.

## Test Framework

**Runner:**
- pytest `>=9.1.1` (dev dependency group in `backend/pyproject.toml`; locked in `backend/uv.lock`)
- pytest-asyncio `>=1.4.0`
- Config: `[tool.pytest.ini_options]` in `backend/pyproject.toml`:
  ```toml
  asyncio_mode = "auto"
  pythonpath = ["."]
  testpaths = ["tests"]
  ```
- There is no `conftest.py` tracked in the repository (a stale `tests/__pycache__/conftest.*.pyc` exists locally but no source file).

**Assertion Library:**
- Plain `assert` statements (pytest rewriting). `pytest.raises` and `pytest.approx` for exceptions and float comparison.

**HTTP testing helpers:**
- `httpx.MockTransport` for simulating Massive REST responses (`backend/tests/market/test_massive.py`).
- `httpx.ASGITransport` for in-process FastAPI calls (`backend/tests/market/test_app.py`).
- `uvicorn.Server` run on a free port for real SSE streaming tests (`backend/tests/market/test_stream.py`).

**Run Commands:**

```bash
cd backend && uv sync                              # Install dev dependencies
cd backend && uv run pytest                        # Run all tests
cd backend && uv run pytest tests/market/test_cache.py          # One file
cd backend && uv run pytest tests/market/test_cache.py::test_first_update_has_flat_direction   # One test
cd backend && uv run pytest -k simulator           # Filter by name
```

- Watch mode: not configured (no `pytest-watch`).
- Coverage: not configured (no `pytest-cov` in dev dependencies, no `.coveragerc`). `.gitignore` already excludes `.coverage`, `htmlcov/`, and `coverage.xml`, so adding coverage later needs no ignore changes.
- Use `uv run` and `uv add` only (user global rule); never `pip install` or `python3 -m pytest`.

## Test File Organization

**Location:**
- Tests live in a separate tree, not co-located with source: `backend/tests/market/` mirrors `backend/app/market/`.

**Naming:**
- Files: `test_<module>.py` matching the source module name (`test_cache.py`, `test_factory.py`, `test_massive.py`, `test_simulator.py`, `test_stream.py`, `test_app.py`).
- Functions: `test_<behavior_in_words>` describing the expected behavior, e.g. `test_change_pct_zero_prev_close`, `test_http_error_keeps_old_prices`, `test_key_selects_massive_with_poll_interval`.
- Helper functions in tests carry no `test_` prefix: `make`, `make_source`, `take`, `log_returns`, `corr`, `parse`, `data_lines`.

**Structure:**

```
backend/tests/
└── market/
    ├── test_app.py        # lifespan wiring + /api/health (full FastAPI app)
    ├── test_cache.py      # PriceCache and PriceUpdate
    ├── test_factory.py    # create_market_source env selection
    ├── test_massive.py    # parse_snapshot and MassiveSource.poll_once
    ├── test_simulator.py  # GBM math, correlation, events, lifecycle
    └── test_stream.py     # price_events generator and live SSE over HTTP
```

- No `__init__.py` in `tests/` or `tests/market/`. Pytest runs with `pythonpath = ["."]` so tests import `app.*` directly.
- Put new tests under `backend/tests/<area>/` following the same layout.

## Test Structure

**Suite Organization:**
Tests are flat module-level functions, grouped by file, with no `class Test...` suites. Setup is done inline at the top of each test, usually with a small factory helper:

```python

# backend/tests/market/test_simulator.py

def make(seed: int = 1) -> tuple[PriceCache, SimulatorSource]:
    cache = PriceCache()
    return cache, SimulatorSource(cache, rng=random.Random(seed))

async def test_known_ticker_seeds_at_seed_price():
    cache, sim = make()
    await sim.add_ticker("AAPL")
    u = cache.get("AAPL")
    assert u.price == SEED_PRICES["AAPL"] and u.prev_close == SEED_PRICES["AAPL"]
```

**Async tests:**
- Declare with `async def` and no marker. `asyncio_mode = "auto"` runs them on an event loop automatically. Do NOT add `@pytest.mark.asyncio`.
- Sync tests are plain `def`.

**Patterns:**
- Setup: construct objects inline or via a `make_*` helper that returns a tuple of `(cache, source)`.
- Teardown: explicit `await source.stop()` at the end of tests that call `start()` (`test_start_seeds_and_runs_in_background`, `test_polling_survives_malformed_payload`). No fixture-based teardown except one case.
- Assertions: compare tuples of fields in one assert when checking related values, e.g. `assert (u.previous_price, u.prev_close, u.direction) == (100.0, 99.0, "up")`.

**Fixtures:**
- Only one fixture is defined: `server` in `backend/tests/market/test_stream.py`, an async fixture that starts a real `uvicorn.Server` on port 0, yields `(app, base_url)`, and shuts down with `should_exit = True`. Use this pattern for any test that needs a live HTTP server.
- No shared fixtures in a `conftest.py`. Add one only when a fixture is used in three or more files.

## Mocking

**Framework:** No `unittest.mock` or `pytest-mock`. Mocking is done with:
1. `monkeypatch` (pytest built-in) for environment variables and module constants.
2. Dependency injection through constructor arguments.
3. `httpx.MockTransport` for HTTP.

**Environment variables:**

```python

# backend/tests/market/test_factory.py

def test_key_selects_massive_with_poll_interval(monkeypatch):
    monkeypatch.setenv("MASSIVE_API_KEY", "abc")
    monkeypatch.setenv("MASSIVE_POLL_SECONDS", "5")
    source = create_market_source(PriceCache())
    assert isinstance(source, MassiveSource)
```

Use `monkeypatch.delenv("X", raising=False)` to ensure absence.

**Module constants (speed up loops or force branches):**

```python

# backend/tests/market/test_simulator.py

def test_events_produce_large_jumps(monkeypatch):
    monkeypatch.setattr(simulator, "EVENT_PROB", 1.0)
```

Patch the module attribute the code reads at call time. `TICK_SECONDS` is patched to `0.01` in background-loop tests.

**Deterministic randomness:**
- Pass `random.Random(seed)` into `SimulatorSource(cache, rng=...)`. Same seed must produce identical output (`test_step_is_deterministic_for_same_seed`).
- For exact math, use a subclass that zeroes shocks:
  ```python
  class ZeroShocks(random.Random):
      def gauss(self, mu: float = 0.0, sigma: float = 1.0) -> float:
          return 0.0
  ```

**HTTP:**

```python

# backend/tests/market/test_massive.py

def make_source(handler, poll_seconds: float = 15.0):
    client = httpx.AsyncClient(
        base_url="https://api.massive.com",
        transport=httpx.MockTransport(handler),
        headers={"Authorization": "Bearer k"},
    )
    cache = PriceCache()
    return cache, MassiveSource(cache, "k", poll_seconds=poll_seconds, client=client)
```

- Inject the mock transport via the `client=` constructor argument. Never hit the real Massive API in tests.
- Simulate failures by returning `httpx.Response(429)`, raising `httpx.ConnectError`, returning invalid bytes, or returning `{"tickers": None}`.

**Private state:**
- Tests set private attributes directly when the public API cannot express the state, e.g. `src._tickers = {"AAPL"}` and `sim._seed("AAPL")`. Prefer the public method when one exists (`start`, `add_ticker`); use private access only to isolate one behavior.

**What to Mock:**
- Environment variables (`monkeypatch.setenv`).
- External HTTP (`httpx.MockTransport`).
- Randomness (seeded `random.Random` or `ZeroShocks`).
- Long intervals and tick durations (`monkeypatch.setattr` on module constants or the `interval=` argument of `price_events`).
- Time, when identity or timestamps matter (`monkeypatch.setattr(cache_module.time, "time", lambda: 1.0)`).

**What NOT to Mock:**
- `PriceCache` and `PriceUpdate`. They are pure in-memory objects; use the real ones.
- The FastAPI app and SSE stream in `test_app.py` and `test_stream.py` (use `ASGITransport` or a real server).
- The GBM math. Test it against the closed-form expression with `pytest.approx(..., rel=1e-12)`.

## Fixtures and Factories

**Test Data:**
- Expected values come from the seed and parameter tables in `backend/app/market/seed_data.py` (`SEED_PRICES`, `GBM_PARAMS`, `SECTORS`), imported directly rather than duplicated.
- Inline sample payloads for Massive responses as module-level constants:
  ```python
  # backend/tests/market/test_massive.py
  SAMPLE = {
      "status": "OK",
      "count": 3,
      "tickers": [
          {"ticker": "AAPL", "lastTrade": {"p": 191.23}, "min": {"c": 191.2}, ...},
      ],
  }
  ```
- Reuse `SAMPLE` across tests and derive variants inline (`payload = {"tickers": [...]}`).

**Location:**
- Inline in each test module. No shared `fixtures/` or `factories/` directory exists.

## Coverage

**Requirements:** None enforced. No coverage threshold in config or CI.

**View Coverage:** not available as configured. To measure temporarily:

```bash
cd backend && uv run --with pytest-cov pytest --cov=app --cov-report=term-missing
```

Do not add `pytest-cov` to dependencies without a request.

## Test Types

**Unit Tests:**
- All current tests. Cover `PriceCache` semantics, `PriceUpdate` direction and change percent, `parse_snapshot` fallback chain, `MassiveSource.poll_once` error resilience, `SimulatorSource` lifecycle and statistics, factory selection, and `price_events` change detection.
- Statistical tests use fixed seeds and tolerances (e.g. log-return std within 5% of expected, correlation within 0.05 of 0.6 / 0.3). Keep the seed and step count when editing them; they are tuned for determinism.

**Integration Tests:**
- `backend/tests/market/test_app.py` runs the real `lifespan` with the simulator and checks `/api/health` via `ASGITransport`.
- `backend/tests/market/test_stream.py::test_stream_over_http` runs a real uvicorn server and reads the SSE wire format (`retry:`, `data:`, `: ping`).
- Both use real asyncio loops and short sleeps; keep them under about one second.

**E2E Tests:**
- Not used yet. `planning/PLAN.md` specifies Playwright tests in `test/` with `docker-compose.test.yml` and `LLM_MOCK=true`. None exist.

## Common Patterns

**Async Testing:**

```python

# backend/tests/market/test_stream.py

async def test_unchanged_tickers_are_not_resent():
    cache = PriceCache()
    cache.update("AAPL", 190.0)
    gen = price_events(cache, interval=0)
    await take(gen, 2)
    with pytest.raises(TimeoutError):
        await asyncio.wait_for(anext(gen), 0.05)
```

- Pull events from async generators with `anext(gen)` and the `take(gen, n)` helper.
- Bound waits with `asyncio.wait_for(..., timeout)`; a timeout is an expected outcome in negative tests.
- For background tasks, poll with `await asyncio.sleep(0.1)` and assert a monotonic change (timestamp advanced, count > N), not an exact tick count.
- Always `await source.stop()` after `start()` so tasks do not leak between tests.

**Error Testing:**

```python

# backend/tests/market/test_cache.py

def test_interface_is_abstract():
    with pytest.raises(TypeError):
        MarketDataSource()
```

- Use `pytest.raises(ExceptionType)` for expected exceptions.
- For resilience, do not expect an exception: call the method and assert the previous state is preserved (`test_http_error_keeps_old_prices`).

**Edge Cases to Keep Covering:**
- Empty string, whitespace-only, and missing env vars for `MASSIVE_API_KEY` (`test_factory.py`).
- Null sections in payloads (`"lastTrade": None`), missing `tickers` list, and zero previous close.
- Idempotent `add_ticker`, `remove_ticker`, `stop()`.
- Same-timestamp updates must still be pushed (identity-based change detection in `price_events`).

## Guidance for New Tests

1. Put the file at `backend/tests/<area>/test_<module>.py`.
2. Write `async def` tests without markers; write sync tests as plain `def`.
3. Inject dependencies via constructors; use `monkeypatch` for env and module constants.
4. Seed any randomness and never call the real Massive API.
5. Run `cd backend && uv run pytest` before committing; run one file while iterating.

---

*Testing analysis: 2026-10-19*
