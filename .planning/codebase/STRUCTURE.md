---
last_mapped_commit: 24a4b2a30df1d0f61a24990f210bc270e83cd728
last_mapped_at: 2026-10-19
---
# Codebase Structure

**Analysis Date:** 2026-10-19

## Directory Layout

```
finally/                         # Repo root
├── backend/                     # FastAPI uv project (implemented: market data only)
│   ├── app/                     # Application package
│   │   ├── __init__.py          # Empty package marker
│   │   ├── main.py              # FastAPI app, lifespan, health route
│   │   └── market/              # Market data subsystem
│   ├── scripts/                 # Developer tools run with uv
│   │   └── watch_prices.py      # Terminal SSE price viewer
│   ├── tests/                   # pytest suite
│   │   └── market/              # Tests for app/market
│   ├── pyproject.toml           # Dependencies, pytest config
│   ├── uv.lock                  # Locked dependencies
│   ├── .python-version          # Python 3.12
│   └── README.md                # Backend readme
├── planning/                    # Project-wide agent docs (spec and design notes)
├── .planning/codebase/          # Generated codebase maps (GSD output, this folder)
├── .claude/                     # GSD tooling and agent definitions (not project code)
├── .env                         # Local secrets, gitignored (never read into docs)
├── .gitignore
├── CLAUDE.md                    # Agent instructions; points at planning/PLAN.md
├── LICENSE
└── README.md                    # Project overview and planned quick start
```

Not present yet, but specified in `planning/PLAN.md`: `frontend/`, `backend/db/`, `db/`, `scripts/` (start/stop wrappers), `test/` (Playwright E2E), `Dockerfile`, `docker-compose.yml`.

## Directory Purposes

**`backend/app/`:**
- Purpose: Python application package served by uvicorn.
- Contains: `main.py` (composition root) and the `market/` subpackage.
- Key files: `backend/app/main.py`

**`backend/app/market/`:**
- Purpose: Everything that produces, caches, and streams prices.
- Contains: source interface, two source implementations, cache, model, factory, seed data, SSE router.
- Key files: `backend/app/market/interface.py`, `backend/app/market/factory.py`, `backend/app/market/simulator.py`, `backend/app/market/massive.py`, `backend/app/market/cache.py`, `backend/app/market/models.py`, `backend/app/market/stream.py`, `backend/app/market/seed_data.py`

**`backend/scripts/`:**
- Purpose: Manual developer tools, not imported by the app.
- Contains: `watch_prices.py`
- Key files: `backend/scripts/watch_prices.py`

**`backend/tests/market/`:**
- Purpose: Unit and integration tests for the market package. Mirrors `app/market/` file by file.
- Contains: `test_app.py`, `test_cache.py`, `test_factory.py`, `test_massive.py`, `test_simulator.py`, `test_stream.py`
- Key files: `backend/tests/market/test_stream.py`, `backend/tests/market/test_simulator.py`

**`planning/`:**
- Purpose: Shared contract between agents.
- Contains: `PLAN.md` (full spec), `MARKET_DATA_DESIGN.md`, `MARKET_DATA_REVIEW.md`, `MARKET_DATA_SUMMARY.md`, `UNDERSTANDING.md`
- Key files: `planning/PLAN.md`, `planning/MARKET_DATA_SUMMARY.md`

**`.claude/`:**
- Purpose: GSD workflow tooling (commands, agents, references). Not application code. Ignore when analyzing the product.

## Key File Locations

**Entry Points:**
- `backend/app/main.py`: ASGI app object `app`, startup/shutdown lifespan, `/api/health`.

**Configuration:**
- `backend/pyproject.toml`: Python version constraint, runtime and dev dependencies, pytest options (`asyncio_mode = "auto"`, `pythonpath = ["."]`, `testpaths = ["tests"]`).
- `backend/.python-version`: `3.12`.
- `backend/app/market/seed_data.py`: default tickers, seed prices, GBM parameters, sectors.
- `.env` (repo root): runtime environment variables such as `MASSIVE_API_KEY` and `OPENROUTER_API_KEY`. Read by the environment at runtime. Contents are not documented here.

**Core Logic:**
- `backend/app/market/simulator.py`: GBM price simulator.
- `backend/app/market/massive.py`: Massive REST poller and `parse_snapshot`.
- `backend/app/market/factory.py`: source selection.
- `backend/app/market/cache.py`: shared price cache.
- `backend/app/market/stream.py`: SSE endpoint.

**Testing:**
- `backend/tests/market/`: all automated tests currently present.
- Run from `backend/`: `uv run pytest`.

## Naming Conventions

**Files:**
- Python modules: `snake_case.py`, one concept per module (`cache.py`, `simulator.py`, `seed_data.py`).
- Tests: `test_<module>.py` under `backend/tests/<area>/`, mirroring the source module name.
- Scripts: `snake_case.py` under `backend/scripts/`.
- Docs in `planning/`: `UPPER_SNAKE_CASE.md`.
- Planned shell scripts (from `planning/PLAN.md`): `start_mac.sh`, `start_windows.ps1`.

**Directories:**
- Python packages: lowercase single words (`app`, `market`, `tests`, `scripts`).
- Top-level planned directories follow `PLAN.md`: `frontend/`, `backend/`, `planning/`, `scripts/`, `test/`, `db/`.

**Code:**
- Classes: `PascalCase` (`PriceCache`, `SimulatorSource`, `MarketDataSource`).
- Functions and variables: `snake_case`. Module constants: `UPPER_SNAKE_CASE` (`PUSH_SECONDS`, `TICK_SECONDS`, `SEED_PRICES`).
- Tickers: upper case strings (`"AAPL"`). The interface docstring says the API layer normalizes them.
- Env vars: `UPPER_SNAKE_CASE` (`MASSIVE_API_KEY`, `MASSIVE_POLL_SECONDS`).

## Where to Add New Code

**New market data source:**
- Implementation: `backend/app/market/<name>.py`, subclass `MarketDataSource` from `backend/app/market/interface.py`.
- Wiring: add a branch in `backend/app/market/factory.py`.
- Tests: `backend/tests/market/test_<name>.py`.

**New API route group (portfolio, watchlist, chat):**
- Implementation: `backend/app/<area>/` as a new package, with a `router = APIRouter(prefix="/api/<area>")`, then `app.include_router(...)` in `backend/app/main.py`. Follow the layout of `backend/app/market/`.
- Tests: `backend/tests/<area>/`.

**Database code (planned):**
- Schema and seed logic: `backend/db/` (per `planning/PLAN.md`). Runtime file: `db/finally.db` at repo root.

**New shared model:**
- Put immutable dataclasses next to their producer or consumer. Shared across packages, put them in a module like `backend/app/market/models.py`.

**Utilities:**
- No shared utilities package exists. Add one under `backend/app/` only when two modules need the same helper.

**Dev tools:**
- `backend/scripts/`. Do not import from `scripts/` in application code.

## Special Directories

**`.planning/codebase/`:**
- Purpose: Generated codebase analysis documents for GSD commands.
- Generated: Yes (by the codebase mapper agent).
- Committed: Depends on the project's `.planning` policy.

**`.claude/`:**
- Purpose: GSD tooling, agent definitions, commands, references.
- Generated: Installed by GSD.
- Committed: Yes (tracked in git).

**`backend/.venv/` (created by `uv sync`):**
- Purpose: Local Python environment.
- Generated: Yes.
- Committed: No (`.venv` is in `.gitignore`).

**`db/` (planned):**
- Purpose: Volume mount point for `finally.db`.
- Generated: Yes, at runtime.
- Committed: Only `.gitkeep`; `finally.db` is gitignored.

---

*Structure analysis: 2026-10-19*
