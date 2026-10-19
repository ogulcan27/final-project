---
last_mapped_commit: 24a4b2a30df1d0f61a24990f210bc270e83cd728
last_mapped_at: 2026-10-19
---
# Coding Conventions

**Analysis Date:** 2026-10-19

## Scope of the Codebase

Only the backend market data layer exists in source form: `backend/app/market/`. The frontend, portfolio, watchlist, chat and database modules described in `planning/PLAN.md` are not yet implemented. Conventions below are derived from `backend/` and `backend/tests/`. Root `CLAUDE.md` and `planning/PLAN.md` are the project-level rules.

## Naming Patterns

**Files:**
- Python modules use short, lowercase snake_case nouns: `backend/app/market/cache.py`, `backend/app/market/factory.py`, `backend/app/market/seed_data.py`.
- Test files are `test_<module>.py` mirroring the source module: `backend/tests/market/test_cache.py` tests `backend/app/market/cache.py`.
- Scripts live in `backend/scripts/` with snake_case names: `backend/scripts/watch_prices.py`.
- Planning documents use UPPER_SNAKE_CASE: `planning/MARKET_DATA_DESIGN.md`.

**Functions and methods:**
- snake_case, verb-first for actions: `create_market_source`, `poll_once`, `parse_snapshot`, `price_events`, `add_ticker`, `remove_ticker`.
- Private helpers are prefixed with a single underscore: `SimulatorSource._seed`, `SimulatorSource._correlated_shock`, `PriceCache._prices`, `MassiveSource._run`.
- Boolean-like and query methods use plain nouns or `get_` prefixes: `PriceCache.get`, `PriceCache.get_price`, `PriceCache.all`.

**Variables:**
- snake_case. Short local names are used for math and loops (`z`, `mu`, `sigma`, `dt`, `p`, `u`); longer names for domain values (`prev_close`, `previous_price`, `sector_weight`).
- Module-level constants are UPPER_SNAKE_CASE: `TICK_SECONDS`, `TRADING_SECONDS_PER_YEAR`, `MARKET_WEIGHT`, `EVENT_PROB` in `backend/app/market/simulator.py`; `BASE_URL`, `SNAPSHOT_PATH` in `backend/app/market/massive.py`; `RETRY_MS`, `PUSH_SECONDS` in `backend/app/market/stream.py`.
- Logger is a module-level `log = logging.getLogger(__name__)` in `backend/app/market/massive.py`.

**Types and classes:**
- PascalCase: `PriceCache`, `PriceUpdate`, `MarketDataSource`, `SimulatorSource`, `MassiveSource`, `ZeroShocks` (test helper).
- Abstract base uses no `Base` prefix: `MarketDataSource(ABC)` in `backend/app/market/interface.py`. Implementations are named `<Variant>Source`.
- Value objects are `@dataclass(frozen=True, slots=True)`: `PriceUpdate` in `backend/app/market/models.py`.

**Tickers:**
- Stored and passed as upper-case strings (`"AAPL"`). `backend/app/market/interface.py` states the API layer normalizes tickers.

## Code Style

**Formatting:**
- No formatter configuration is committed (no `ruff`, `black`, `.editorconfig`, or `.prettierrc` in the repo).
- Observed style: 4-space indentation, double quotes, trailing commas in multi-line literals, lines generally kept under ~90 characters.
- Multi-item dict/list literals are sometimes packed several per line in data files, e.g. `backend/app/market/seed_data.py`:
  ```python
  SEED_PRICES: dict[str, float] = {
      "AAPL": 190.0, "GOOGL": 175.0, "MSFT": 420.0, "AMZN": 185.0, "TSLA": 250.0,
  ```
- Follow this packing style only for constant data tables; keep logic one statement per line.

**Linting:**
- Not configured. No lint step is defined in `backend/pyproject.toml`.
- Do not introduce a linter config without a phase that asks for it; if added, use `ruff` (per the user's global "latest APIs" rule).

**Type hints:**
- Required on all public signatures. Modern syntax is used throughout: `list[str]`, `dict[str, float]`, `X | None`, `tuple[float, float]`. Do not use `typing.Optional`, `typing.List`, or `typing.Dict`.
- Return types are annotated on public functions and methods (`-> PriceUpdate`, `-> list[str]`, `-> None`). Test functions are not annotated.
- Properties that expose state are annotated: `@property def tickers(self) -> list[str]`.

**Python version:** 3.12 (`backend/.python-version`, `requires-python = ">=3.12"` in `backend/pyproject.toml`). Use 3.12 features freely (`X | Y` unions, builtin generics, `anext`).

## Import Organization

**Order (observed):**
1. Standard library (`asyncio`, `contextlib`, `math`, `random`, `logging`, `os`, `time`)
2. Third-party (`httpx`, `fastapi`, `fastapi.sse`, `uvicorn`, `pytest`)
3. Local (`from .cache import PriceCache`, `from app.market import ...`)

Groups are separated by a blank line.

**Relative vs absolute:**
- Inside the `app.market` package, modules use relative imports: `from .cache import PriceCache`, `from .interface import MarketDataSource` (`backend/app/market/simulator.py`, `backend/app/market/massive.py`).
- Code outside the package uses absolute imports from `app`: `from app.market import PriceCache, create_market_source` (`backend/app/main.py`, tests).
- Tests import from the public package `app.market` where possible and reach into submodules only when patching (`from app.market import simulator`, `from app.market import cache as cache_module`).

**Path aliases:** None. `pyproject.toml` sets `pythonpath = ["."]` for pytest only.

**Re-exports:**
- The package `backend/app/market/__init__.py` is the public barrel: it imports and lists `__all__ = ["MarketDataSource", "PriceCache", "PriceUpdate", "create_market_source"]`. Outside code should import from `app.market`, not from private modules, unless it needs a concrete class such as `SimulatorSource` or `MassiveSource` (see `backend/app/market/factory.py`).

## Error Handling

**General approach (observed):**
- Expected external failures are caught narrowly and logged, not raised. `MassiveSource.poll_once` in `backend/app/market/massive.py` catches `httpx.HTTPError` with `log.warning(...)` and catches `Exception` with `log.exception(...)`, then returns. The previous cache values are kept.
- Polling loops never die from one bad response: `poll_once` is called inside `_run` without an outer try.
- Idempotent operations are preferred over raising: `SimulatorSource.add_ticker` ignores known tickers, `remove_ticker` pops with a default, `PriceCache.remove` uses `pop(ticker, None)`.
- Cancellation on shutdown uses `contextlib.suppress(asyncio.CancelledError)` after `task.cancel()` (`backend/app/market/simulator.py`, `backend/app/market/massive.py`).
- Zero-division is guarded explicitly with early returns, not exceptions: `PriceUpdate.change_pct` returns `0.0` when `prev_close == 0`; `pct()` in `backend/scripts/watch_prices.py` returns `0.0` when the base is falsy.
- Missing data is `None`, not an exception: `PriceCache.get` and `get_price` return `None` for unknown tickers.
- No custom exception classes exist in the codebase.

**Guidance for new code:**
- Follow the project rule: no defensive programming, exception managers only where a failure is expected at a real boundary (network, external JSON). Do not wrap internal calls in try/except.

## Logging

**Framework:** standard library `logging`, with one module logger per file: `log = logging.getLogger(__name__)`.

**Patterns:**
- Use `%s`-style lazy formatting: `log.warning("Massive poll failed: %s", exc)`.
- `log.warning` for recoverable external failures; `log.exception` only for unexpected errors where the traceback matters.
- No `print` in library code. `print` and `rich` output are used only in the standalone `backend/scripts/watch_prices.py`.
- Do not use emojis in log or print text (user global rule).

## Comments and Docstrings

**Docstrings:**
- Used on every class and on most public functions and methods. They are short, one or two sentences, in imperative or descriptive mood, and state behavior and invariants rather than restating the signature. Examples:
  - `"""Store a new price and keep the old price as previous_price.` (`backend/app/market/cache.py`)
  - `"""One snapshot request for all tracked tickers.` (`backend/app/market/massive.py`)
  - `"""Map values to unicode block characters scaled between their min and max."""` (`backend/scripts/watch_prices.py`)
- Multi-line docstrings start on the first line after the opening quotes and close on their own line for classes that document fields or invariants (`PriceUpdate`, `MarketDataSource`).
- Abstract method docstrings describe the contract, including idempotence: `"""Start tracking a ticker. Idempotent."""` (`backend/app/market/interface.py`).
- Module docstrings are used in scripts and seed data (`backend/scripts/watch_prices.py` contains a usage line; `backend/app/market/seed_data.py` one-liner).

**Inline comments:**
- Sparse. Used to explain non-obvious math or design decisions, e.g. `# unrounded internal state` in `backend/app/market/simulator.py`, `# prime the cache so the first SSE push has data` in `backend/app/market/massive.py`, `# (annual drift mu, annual volatility sigma)` in `backend/app/market/seed_data.py`.
- Do not add comments that restate code.

**TODO comments:**
- One known TODO: `backend/app/main.py` in `lifespan` ("replace DEFAULT_TICKERS with watchlist UNION open positions from SQLite"). Use the `TODO:` prefix with a concrete action.

## Function and Class Design

**Size:**
- Functions are short. The longest in the codebase is `SimulatorSource.step` (about 10 lines) and `watch_prices.py` display builders. Keep each function focused on one job; split helpers into named private methods (`_seed`, `_run`, `_correlated_shock`).

**Parameters:**
- Positional for required domain values; keyword-only defaults for tuning: `PriceCache.update(ticker, price, prev_close=None)`, `price_events(cache, interval=PUSH_SECONDS)`, `MassiveSource(cache, api_key, poll_seconds=15.0, client=None)`.
- Dependencies are injected through constructors with optional overrides for tests: `SimulatorSource(cache, rng=None)` uses `rng or random.Random()`; `MassiveSource(..., client=None)` builds an `httpx.AsyncClient` only when none is passed.

**Return values:**
- Mutators return the created value when useful: `PriceCache.update` returns the new `PriceUpdate`.
- Lookups return `Optional` (`X | None`) rather than raising.
- Async methods return `None` unless data is needed.

**Dataclasses and state:**
- Immutable value types use `@dataclass(frozen=True, slots=True)`.
- Mutable runtime state is held in plain instance attributes with a leading underscore (`self._prices`, `self._task`, `self._tickers`).

**Async:**
- Long-running work is started with `asyncio.create_task` in `start()` and cancelled in `stop()`. `start()`/`stop()` are idempotent (`if self._task:` guard, reset to `None`).
- Code assumes one event loop; `PriceCache` has no locks by design (`backend/app/market/cache.py` docstring).

## Module Design

**Exports:**
- Public names are defined by the package `__all__` in `backend/app/market/__init__.py`.
- Each implementation lives in its own module behind the `MarketDataSource` ABC: `simulator.py`, `massive.py`. The selection logic lives only in `backend/app/market/factory.py`.

**Barrel files:**
- `backend/app/market/__init__.py` is the only barrel. Do not create barrels elsewhere until a package has several public modules.

**Environment configuration:**
- Read in one place per concern with `os.getenv` and an explicit default; strip whitespace on secrets: `os.getenv("MASSIVE_API_KEY", "").strip()` in `backend/app/market/factory.py`. Parse numbers at the point of use with `float(...)`.
- Only `factory.py` reads `MASSIVE_API_KEY` and `MASSIVE_POLL_SECONDS`.

**Pattern for adding a new market source:**
1. Subclass `MarketDataSource` in a new module under `backend/app/market/`.
2. Implement `start`, `stop`, `add_ticker`, `remove_ticker`, and the `tickers` property; write to the shared `PriceCache` via `cache.update(...)`.
3. Add a branch in `create_market_source` in `backend/app/market/factory.py`.
4. Export from `backend/app/market/__init__.py` only if the factory does not already hide it.

## Frontend Conventions

Not applicable yet. No frontend source exists under `frontend/`. The planned Tailwind dark theme colors in `planning/PLAN.md` (`#0d1117`, `#ecad0a`, `#209dd7`, `#753991`) are the design contract for when the frontend is added.

---

*Convention analysis: 2026-10-19*
