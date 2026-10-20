<!-- GSD:project-start source:PROJECT.md -->

## Project

**FinAlly — AI Trading Workstation**

FinAlly (Finance Ally) is a trading-practice workstation for complete beginners who want to learn how trading works. It streams live (real or simulated) market prices, lets the user trade a $10,000 simulated portfolio, and pairs every action with its outcome so the learner sees immediately what a trade did to their profit. It looks like a Bloomberg terminal, but speaks plain language, and an AI coach explains concepts, executes trades on request, and reviews past decisions.

The full product specification lives in `planning/PLAN.md`; this document captures scope, decisions, and additions made on top of it.

**Core Value:** A beginner can place a trade and instantly see — on the charts, in the numbers, and in the trade history — how that action affects their profit, with an AI coach ready to explain what happened.

### Constraints

- **Tech stack**: FastAPI + uv (Python 3.12), Next.js TypeScript static export, Tailwind, SQLite, SSE, LiteLLM → OpenRouter — fixed by PLAN.md
- **Packaging**: Python via `uv` only (`uv run`, `uv add`), never pip/python3 directly — user rule
- **Deployment**: single Docker container, single port 8000 — PLAN.md
- **LLM**: `openrouter/nvidia/nemotron-3-super-120b-a12b:free` with `provider.require_parameters: true` and structured outputs, via the openrouter-inference skill — PLAN.md
- **Ports**: app runs in Docker on 8000; local test servers use 8020 — user preference
- **Secrets**: `.env` is never read into agent context; keys only via environment
- **Code style**: simple, incremental, short modules, latest library APIs, no emojis, no defensive over-engineering — user rule
- **Git**: user commits code; `.planning/` docs not committed (`commit_docs: false`)

<!-- GSD:project-end -->

<!-- GSD:stack-start source:codebase/STACK.md -->

## Technology Stack

## Languages

- Python 3.12 (`>=3.12` in `backend/pyproject.toml`, pinned in `backend/.python-version`) - all implemented server code in `backend/app/`, tests in `backend/tests/`, and the dev script `backend/scripts/watch_prices.py`
- TypeScript - planned for `frontend/` (Next.js). Not present in the repository yet.
- Bash / PowerShell - planned start/stop scripts in `scripts/`. Not present yet.

## Runtime

- CPython 3.12 (the only runtime implemented so far)
- Planned container runtime: Python 3.12 slim image (Dockerfile not yet present; see `planning/PLAN.md` section 11)
- `uv` (Astral) - manages the backend project
- Lockfile: present - `backend/uv.lock`
- Python version file: `backend/.python-version` (`3.12`)

## Frameworks

- FastAPI `0.143.1` - HTTP API and SSE endpoints. Uses the native `fastapi.sse.EventSourceResponse` and `ServerSentEvent` in `backend/app/market/stream.py`. App entry point: `backend/app/main.py` (`app = FastAPI(lifespan=...)`).
- Starlette `1.8.0` - transitive ASGI layer under FastAPI
- Uvicorn `0.54.0` - ASGI server, run as `uvicorn app.main:app --port 8000`
- Pydantic `2.14.1` - transitive; models and validation under FastAPI
- Next.js with TypeScript, built as a static export (`output: 'export'`) and served by FastAPI from `/`
- Tailwind CSS for styling (per `planning/PLAN.md` section 10)
- Canvas charting library: Lightweight Charts or Recharts (per `planning/PLAN.md` section 10)
- pytest `9.1.1` - backend test runner. Config in `backend/pyproject.toml` (`[tool.pytest.ini_options]`: `asyncio_mode = "auto"`, `pythonpath = ["."]`, `testpaths = ["tests"]`)
- pytest-asyncio `1.4.0` - async test support
- Test files: `backend/tests/market/` (test_app, test_cache, test_factory, test_massive, test_simulator, test_stream)
- Playwright E2E tests in `test/` - planned, not present
- `uv` - dependency resolution, `uv sync`, `uv run`
- `uv run --env-file ../.env` - loads the root `.env` when running the backend locally (documented in `backend/README.md`)
- Docker multi-stage build - planned (`Dockerfile` at repo root, not present yet)

## Key Dependencies

- `fastapi>=0.143.1` (locked 0.143.1) - web framework and SSE
- `httpx>=0.28.1` (locked 0.28.1) - async HTTP client used by `MassiveSource` in `backend/app/market/massive.py` (`httpx.AsyncClient`, 10s timeout). The Massive SDK is intentionally not used.
- `uvicorn>=0.54.0` (locked 0.54.0) - ASGI server
- `pytest>=9.1.1`, `pytest-asyncio>=1.4.0`
- `rich>=15.0.0` - terminal rendering in `backend/scripts/watch_prices.py` (live price board using `rich.live`, `rich.table`, `rich.panel`)
- anyio 4.15.1, starlette 1.8.0, pydantic 2.14.1, pydantic-core, annotated-types, annotated-doc, typing-extensions, typing-inspection, h11, httpcore, certifi, idna, click, colorama, markdown-it-py, mdurl, pygments, packaging, pluggy, iniconfig, opentelemetry-api
- LiteLLM (LLM calls via OpenRouter, model `openrouter/nvidia/nemotron-3-super-120b-a12b:free`, `provider.require_parameters: true`). Required by `planning/PLAN.md` section 9. No LLM code exists yet, so it is not in `pyproject.toml`. Add with `uv add litellm`.
- `asyncio` (background market task, SSE loop), `math`/`random` (GBM simulator), `logging`, `os` (env vars), `contextlib`, `dataclasses`

## Configuration

- `MASSIVE_API_KEY` - read in `backend/app/market/factory.py`. Non-empty (after strip) selects `MassiveSource`; otherwise `SimulatorSource`.
- `MASSIVE_POLL_SECONDS` - read in `backend/app/market/factory.py`. Poll interval for Massive, default `15`.
- `OPENROUTER_API_KEY` - required for the AI chat. Specified in `planning/PLAN.md`; not read by any code yet.
- `LLM_MOCK` - `true` returns deterministic mock LLM replies. Specified in `planning/PLAN.md`; not implemented yet.
- A root-level `.env` file exists (gitignored by the `.env` rule in `.gitignore`). It holds the environment configuration and was not read for this document.
- `.env.example` is referenced by `README.md` and `planning/PLAN.md` but is not present in the repository yet.
- The backend reads env vars from the process environment. Local runs use `uv run --env-file ../.env`. Docker runs are planned to use `--env-file .env`.
- `backend/pyproject.toml` - project metadata, dependencies, dev group, pytest config
- `backend/uv.lock` - locked dependency graph
- `backend/.python-version` - `3.12`
- `.gitignore` - ignores `.env`, `.envrc`, `.venv`, `db.sqlite3`, and standard Python artifacts
- SQLite, single file `db/finally.db` (volume-mounted at `/app/db` in the container). Not yet implemented: no `db/` directory and no `sqlite3` usage in the code. The stdlib `sqlite3` module is expected to be used, as no ORM is declared.

## Platform Requirements

- Python 3.12 and `uv` installed
- Run backend: `cd backend && uv sync && uv run --env-file ../.env uvicorn app.main:app --port 8000`
- Run tests: `cd backend && uv run pytest`
- Run price board: `uv run scripts/watch_prices.py [base_url]` (needs the server running on port 8000)
- Windows host is in use for this repository (PowerShell is the primary shell)
- Single Docker container on port 8000 (planned): Node 20 slim stage builds the Next.js export, Python 3.12 slim stage runs uvicorn and serves `/api/*` plus static files
- Deploy targets named in `planning/PLAN.md`: local Docker, AWS App Runner, Render, or any container platform

<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->

## Conventions

## Scope of the Codebase

## Naming Patterns

- Python modules use short, lowercase snake_case nouns: `backend/app/market/cache.py`, `backend/app/market/factory.py`, `backend/app/market/seed_data.py`.
- Test files are `test_<module>.py` mirroring the source module: `backend/tests/market/test_cache.py` tests `backend/app/market/cache.py`.
- Scripts live in `backend/scripts/` with snake_case names: `backend/scripts/watch_prices.py`.
- Planning documents use UPPER_SNAKE_CASE: `planning/MARKET_DATA_DESIGN.md`.
- snake_case, verb-first for actions: `create_market_source`, `poll_once`, `parse_snapshot`, `price_events`, `add_ticker`, `remove_ticker`.
- Private helpers are prefixed with a single underscore: `SimulatorSource._seed`, `SimulatorSource._correlated_shock`, `PriceCache._prices`, `MassiveSource._run`.
- Boolean-like and query methods use plain nouns or `get_` prefixes: `PriceCache.get`, `PriceCache.get_price`, `PriceCache.all`.
- snake_case. Short local names are used for math and loops (`z`, `mu`, `sigma`, `dt`, `p`, `u`); longer names for domain values (`prev_close`, `previous_price`, `sector_weight`).
- Module-level constants are UPPER_SNAKE_CASE: `TICK_SECONDS`, `TRADING_SECONDS_PER_YEAR`, `MARKET_WEIGHT`, `EVENT_PROB` in `backend/app/market/simulator.py`; `BASE_URL`, `SNAPSHOT_PATH` in `backend/app/market/massive.py`; `RETRY_MS`, `PUSH_SECONDS` in `backend/app/market/stream.py`.
- Logger is a module-level `log = logging.getLogger(__name__)` in `backend/app/market/massive.py`.
- PascalCase: `PriceCache`, `PriceUpdate`, `MarketDataSource`, `SimulatorSource`, `MassiveSource`, `ZeroShocks` (test helper).
- Abstract base uses no `Base` prefix: `MarketDataSource(ABC)` in `backend/app/market/interface.py`. Implementations are named `<Variant>Source`.
- Value objects are `@dataclass(frozen=True, slots=True)`: `PriceUpdate` in `backend/app/market/models.py`.
- Stored and passed as upper-case strings (`"AAPL"`). `backend/app/market/interface.py` states the API layer normalizes tickers.

## Code Style

- No formatter configuration is committed (no `ruff`, `black`, `.editorconfig`, or `.prettierrc` in the repo).
- Observed style: 4-space indentation, double quotes, trailing commas in multi-line literals, lines generally kept under ~90 characters.
- Multi-item dict/list literals are sometimes packed several per line in data files, e.g. `backend/app/market/seed_data.py`:
- Follow this packing style only for constant data tables; keep logic one statement per line.
- Not configured. No lint step is defined in `backend/pyproject.toml`.
- Do not introduce a linter config without a phase that asks for it; if added, use `ruff` (per the user's global "latest APIs" rule).
- Required on all public signatures. Modern syntax is used throughout: `list[str]`, `dict[str, float]`, `X | None`, `tuple[float, float]`. Do not use `typing.Optional`, `typing.List`, or `typing.Dict`.
- Return types are annotated on public functions and methods (`-> PriceUpdate`, `-> list[str]`, `-> None`). Test functions are not annotated.
- Properties that expose state are annotated: `@property def tickers(self) -> list[str]`.

## Import Organization

- Inside the `app.market` package, modules use relative imports: `from .cache import PriceCache`, `from .interface import MarketDataSource` (`backend/app/market/simulator.py`, `backend/app/market/massive.py`).
- Code outside the package uses absolute imports from `app`: `from app.market import PriceCache, create_market_source` (`backend/app/main.py`, tests).
- Tests import from the public package `app.market` where possible and reach into submodules only when patching (`from app.market import simulator`, `from app.market import cache as cache_module`).
- The package `backend/app/market/__init__.py` is the public barrel: it imports and lists `__all__ = ["MarketDataSource", "PriceCache", "PriceUpdate", "create_market_source"]`. Outside code should import from `app.market`, not from private modules, unless it needs a concrete class such as `SimulatorSource` or `MassiveSource` (see `backend/app/market/factory.py`).

## Error Handling

- Expected external failures are caught narrowly and logged, not raised. `MassiveSource.poll_once` in `backend/app/market/massive.py` catches `httpx.HTTPError` with `log.warning(...)` and catches `Exception` with `log.exception(...)`, then returns. The previous cache values are kept.
- Polling loops never die from one bad response: `poll_once` is called inside `_run` without an outer try.
- Idempotent operations are preferred over raising: `SimulatorSource.add_ticker` ignores known tickers, `remove_ticker` pops with a default, `PriceCache.remove` uses `pop(ticker, None)`.
- Cancellation on shutdown uses `contextlib.suppress(asyncio.CancelledError)` after `task.cancel()` (`backend/app/market/simulator.py`, `backend/app/market/massive.py`).
- Zero-division is guarded explicitly with early returns, not exceptions: `PriceUpdate.change_pct` returns `0.0` when `prev_close == 0`; `pct()` in `backend/scripts/watch_prices.py` returns `0.0` when the base is falsy.
- Missing data is `None`, not an exception: `PriceCache.get` and `get_price` return `None` for unknown tickers.
- No custom exception classes exist in the codebase.
- Follow the project rule: no defensive programming, exception managers only where a failure is expected at a real boundary (network, external JSON). Do not wrap internal calls in try/except.

## Logging

- Use `%s`-style lazy formatting: `log.warning("Massive poll failed: %s", exc)`.
- `log.warning` for recoverable external failures; `log.exception` only for unexpected errors where the traceback matters.
- No `print` in library code. `print` and `rich` output are used only in the standalone `backend/scripts/watch_prices.py`.
- Do not use emojis in log or print text (user global rule).

## Comments and Docstrings

- Used on every class and on most public functions and methods. They are short, one or two sentences, in imperative or descriptive mood, and state behavior and invariants rather than restating the signature. Examples:
- Multi-line docstrings start on the first line after the opening quotes and close on their own line for classes that document fields or invariants (`PriceUpdate`, `MarketDataSource`).
- Abstract method docstrings describe the contract, including idempotence: `"""Start tracking a ticker. Idempotent."""` (`backend/app/market/interface.py`).
- Module docstrings are used in scripts and seed data (`backend/scripts/watch_prices.py` contains a usage line; `backend/app/market/seed_data.py` one-liner).
- Sparse. Used to explain non-obvious math or design decisions, e.g. `# unrounded internal state` in `backend/app/market/simulator.py`, `# prime the cache so the first SSE push has data` in `backend/app/market/massive.py`, `# (annual drift mu, annual volatility sigma)` in `backend/app/market/seed_data.py`.
- Do not add comments that restate code.
- One known TODO: `backend/app/main.py` in `lifespan` ("replace DEFAULT_TICKERS with watchlist UNION open positions from SQLite"). Use the `TODO:` prefix with a concrete action.

## Function and Class Design

- Functions are short. The longest in the codebase is `SimulatorSource.step` (about 10 lines) and `watch_prices.py` display builders. Keep each function focused on one job; split helpers into named private methods (`_seed`, `_run`, `_correlated_shock`).
- Positional for required domain values; keyword-only defaults for tuning: `PriceCache.update(ticker, price, prev_close=None)`, `price_events(cache, interval=PUSH_SECONDS)`, `MassiveSource(cache, api_key, poll_seconds=15.0, client=None)`.
- Dependencies are injected through constructors with optional overrides for tests: `SimulatorSource(cache, rng=None)` uses `rng or random.Random()`; `MassiveSource(..., client=None)` builds an `httpx.AsyncClient` only when none is passed.
- Mutators return the created value when useful: `PriceCache.update` returns the new `PriceUpdate`.
- Lookups return `Optional` (`X | None`) rather than raising.
- Async methods return `None` unless data is needed.
- Immutable value types use `@dataclass(frozen=True, slots=True)`.
- Mutable runtime state is held in plain instance attributes with a leading underscore (`self._prices`, `self._task`, `self._tickers`).
- Long-running work is started with `asyncio.create_task` in `start()` and cancelled in `stop()`. `start()`/`stop()` are idempotent (`if self._task:` guard, reset to `None`).
- Code assumes one event loop; `PriceCache` has no locks by design (`backend/app/market/cache.py` docstring).

## Module Design

- Public names are defined by the package `__all__` in `backend/app/market/__init__.py`.
- Each implementation lives in its own module behind the `MarketDataSource` ABC: `simulator.py`, `massive.py`. The selection logic lives only in `backend/app/market/factory.py`.
- `backend/app/market/__init__.py` is the only barrel. Do not create barrels elsewhere until a package has several public modules.
- Read in one place per concern with `os.getenv` and an explicit default; strip whitespace on secrets: `os.getenv("MASSIVE_API_KEY", "").strip()` in `backend/app/market/factory.py`. Parse numbers at the point of use with `float(...)`.
- Only `factory.py` reads `MASSIVE_API_KEY` and `MASSIVE_POLL_SECONDS`.

## Frontend Conventions

<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->

## Architecture

## Current Scope

## System Overview

```text

```

## Pattern Overview

- One process, one event loop (`asyncio`). The cache has no locks; `backend/app/market/cache.py` documents this.
- Producers (`SimulatorSource`, `MassiveSource`) run as background `asyncio` tasks started in the FastAPI lifespan.
- Consumers (SSE endpoint) poll the cache on a fixed interval rather than receiving pushes from producers.
- Source selection is by environment variable at startup, not per request.
- Data is in memory only. No database is wired yet (`planning/PLAN.md` specifies SQLite at `db/finally.db`).

## Layers

- Purpose: Build the cache, pick the source, start and stop it, mount routers.
- Location: `backend/app/main.py`
- Contains: `lifespan` async context manager, `FastAPI` instance `app`, `/api/health` route.
- Depends on: `app.market` (package exports), `app.market.seed_data.DEFAULT_TICKERS`, `app.market.stream.router`.
- Used by: uvicorn (entry point), tests in `backend/tests/market/test_app.py`.
- Purpose: Single import surface for the market package.
- Location: `backend/app/market/__init__.py`
- Contains: re-exports `MarketDataSource`, `PriceCache`, `PriceUpdate`, `create_market_source`.
- Depends on: `cache`, `factory`, `interface`, `models`.
- Used by: `app/main.py`.
- Purpose: Define the contract every source implements.
- Location: `backend/app/market/interface.py`
- Contains: abstract `MarketDataSource` with `start`, `stop`, `add_ticker`, `remove_ticker`, and the `tickers` property.
- Depends on: nothing in-app.
- Used by: `simulator.py`, `massive.py`, `factory.py`.
- Purpose: Generate or fetch prices and write them into `PriceCache`.
- Location: `backend/app/market/simulator.py` (GBM simulator), `backend/app/market/massive.py` (Massive REST poller).
- Contains: `SimulatorSource`, `MassiveSource`, `parse_snapshot` (pure function in `massive.py`).
- Depends on: `PriceCache`, `MarketDataSource`, `seed_data`; `httpx` for Massive.
- Used by: `factory.py` via `create_market_source`.
- Purpose: Hold the latest `PriceUpdate` per ticker.
- Location: `backend/app/market/cache.py`
- Contains: `PriceCache` with `update`, `get`, `get_price`, `all`, `remove`, `__contains__`.
- Depends on: `models.PriceUpdate`.
- Used by: all producers (writes), `stream.py` and `main.py` (reads).
- Purpose: Immutable price snapshot with derived fields.
- Location: `backend/app/market/models.py`
- Contains: frozen, slotted dataclass `PriceUpdate` with `direction`, `change_pct`, `to_dict()`.
- Depends on: nothing.
- Used by: cache, producers, SSE serializer.
- Purpose: Stream cache contents to browser clients.
- Location: `backend/app/market/stream.py`
- Contains: `APIRouter(prefix="/api/stream")`, `price_events` async generator, `stream_prices` route.
- Depends on: `PriceCache`, `PriceUpdate`, FastAPI's `fastapi.sse` (`EventSourceResponse`, `ServerSentEvent`).
- Used by: mounted in `app/main.py`; consumed by `scripts/watch_prices.py` and, later, the frontend.
- Purpose: Default tickers, seed prices, GBM drift/volatility, sector groups.
- Location: `backend/app/market/seed_data.py`
- Contains: `DEFAULT_TICKERS`, `SEED_PRICES`, `GBM_PARAMS`, `DEFAULT_PARAMS`, `SECTORS`.
- Used by: `simulator.py`, `main.py`.

## Data Flow

### Primary Price Path (simulator)

### Price Path (Massive)

### Shutdown

- Server state: `app.state.price_cache` and `app.state.market_source`, set in `lifespan`. Route handlers read `request.app.state.price_cache`.
- Client state: none on the server. The SSE sender tracks `last_sent` per connection.
- Persistent state: none yet.

## Key Abstractions

- Purpose: Swap simulator and real data without changing downstream code.
- Examples: `backend/app/market/interface.py`, `backend/app/market/simulator.py`, `backend/app/market/massive.py`
- Pattern: Abstract base class with async lifecycle methods (`start`/`stop`) and ticker management (`add_ticker`/`remove_ticker`, both idempotent per the docstring).
- Purpose: Single source of latest prices shared by producers and readers.
- Examples: `backend/app/market/cache.py`
- Pattern: Plain in-memory dict. Identity of `PriceUpdate` objects is used as the change marker for SSE.
- Purpose: Immutable snapshot used for both transport and UI direction (flash) and daily change %.
- Examples: `backend/app/market/models.py`
- Pattern: Frozen slotted dataclass with derived properties.
- Purpose: Environment-based selection of the source implementation.
- Examples: `backend/app/market/factory.py`
- Pattern: Function that returns the interface type.

## Entry Points

- Location: `backend/app/main.py` (`app = FastAPI(lifespan=lifespan)`)
- Triggers: `uvicorn app.main:app` run from `backend/`. The planned Dockerfile CMD is not yet present.
- Responsibilities: start/stop market source, serve `/api/health` and `/api/stream/prices`.
- Location: `backend/app/main.py` (`GET /api/health`)
- Triggers: HTTP GET.
- Responsibilities: returns `{"status": "ok"}`.
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

### Route-level data access through `app.state`

### SSE change detection by object identity

## Error Handling

- `SimulatorSource.stop` suppresses `asyncio.CancelledError` only.
- `parse_snapshot` skips entries with no usable price instead of raising.
- Massive HTTP errors are handled inside `backend/app/market/massive.py` (see the module for the polling loop).

## Cross-Cutting Concerns

## Planned but Not Yet Present

- SQLite persistence (`backend/db/`, runtime file `db/finally.db`)
- Portfolio and trade execution, portfolio snapshot task (every 30 s)
- Watchlist REST endpoints and portfolio REST endpoints
- Chat endpoint with LiteLLM -> OpenRouter and structured trade output
- Next.js frontend in `frontend/` served as a static export from FastAPI

<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->

## Project Skills

| Skill | Description | Path |
|-------|-------------|------|
| openrouter-inference | Use this to write code to call an LLM using LiteLLM and OpenRouter with the free NVIDIA Nemotron 3 Super model and Structured Outputs | `.claude/skills/openrouter/SKILL.md` |
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->

## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-fast` for a trivial task inline, with no subagents and no PLAN.md
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->

## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
