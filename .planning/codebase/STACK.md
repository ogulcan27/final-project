---
last_mapped_commit: 24a4b2a30df1d0f61a24990f210bc270e83cd728
last_mapped_at: 2026-10-19
---
# Technology Stack

**Analysis Date:** 2026-10-19

## Languages

**Primary:**
- Python 3.12 (`>=3.12` in `backend/pyproject.toml`, pinned in `backend/.python-version`) - all implemented server code in `backend/app/`, tests in `backend/tests/`, and the dev script `backend/scripts/watch_prices.py`

**Secondary:**
- TypeScript - planned for `frontend/` (Next.js). Not present in the repository yet.
- Bash / PowerShell - planned start/stop scripts in `scripts/`. Not present yet.

## Runtime

**Environment:**
- CPython 3.12 (the only runtime implemented so far)
- Planned container runtime: Python 3.12 slim image (Dockerfile not yet present; see `planning/PLAN.md` section 11)

**Package Manager:**
- `uv` (Astral) - manages the backend project
- Lockfile: present - `backend/uv.lock`
- Python version file: `backend/.python-version` (`3.12`)

## Frameworks

**Core:**
- FastAPI `0.143.1` - HTTP API and SSE endpoints. Uses the native `fastapi.sse.EventSourceResponse` and `ServerSentEvent` in `backend/app/market/stream.py`. App entry point: `backend/app/main.py` (`app = FastAPI(lifespan=...)`).
- Starlette `1.8.0` - transitive ASGI layer under FastAPI
- Uvicorn `0.54.0` - ASGI server, run as `uvicorn app.main:app --port 8000`
- Pydantic `2.14.1` - transitive; models and validation under FastAPI

**Frontend (planned, not yet present):**
- Next.js with TypeScript, built as a static export (`output: 'export'`) and served by FastAPI from `/`
- Tailwind CSS for styling (per `planning/PLAN.md` section 10)
- Canvas charting library: Lightweight Charts or Recharts (per `planning/PLAN.md` section 10)

**Testing:**
- pytest `9.1.1` - backend test runner. Config in `backend/pyproject.toml` (`[tool.pytest.ini_options]`: `asyncio_mode = "auto"`, `pythonpath = ["."]`, `testpaths = ["tests"]`)
- pytest-asyncio `1.4.0` - async test support
- Test files: `backend/tests/market/` (test_app, test_cache, test_factory, test_massive, test_simulator, test_stream)
- Playwright E2E tests in `test/` - planned, not present

**Build/Dev:**
- `uv` - dependency resolution, `uv sync`, `uv run`
- `uv run --env-file ../.env` - loads the root `.env` when running the backend locally (documented in `backend/README.md`)
- Docker multi-stage build - planned (`Dockerfile` at repo root, not present yet)

## Key Dependencies

**Critical (declared in `backend/pyproject.toml` `[project] dependencies`):**
- `fastapi>=0.143.1` (locked 0.143.1) - web framework and SSE
- `httpx>=0.28.1` (locked 0.28.1) - async HTTP client used by `MassiveSource` in `backend/app/market/massive.py` (`httpx.AsyncClient`, 10s timeout). The Massive SDK is intentionally not used.
- `uvicorn>=0.54.0` (locked 0.54.0) - ASGI server

**Dev group (`[dependency-groups] dev`):**
- `pytest>=9.1.1`, `pytest-asyncio>=1.4.0`
- `rich>=15.0.0` - terminal rendering in `backend/scripts/watch_prices.py` (live price board using `rich.live`, `rich.table`, `rich.panel`)

**Transitive (in `backend/uv.lock`):**
- anyio 4.15.1, starlette 1.8.0, pydantic 2.14.1, pydantic-core, annotated-types, annotated-doc, typing-extensions, typing-inspection, h11, httpcore, certifi, idna, click, colorama, markdown-it-py, mdurl, pygments, packaging, pluggy, iniconfig, opentelemetry-api

**Planned, not yet declared:**
- LiteLLM (LLM calls via OpenRouter, model `openrouter/nvidia/nemotron-3-super-120b-a12b:free`, `provider.require_parameters: true`). Required by `planning/PLAN.md` section 9. No LLM code exists yet, so it is not in `pyproject.toml`. Add with `uv add litellm`.

**Standard library in use:**
- `asyncio` (background market task, SSE loop), `math`/`random` (GBM simulator), `logging`, `os` (env vars), `contextlib`, `dataclasses`

## Configuration

**Environment variables (names only; values are never recorded here):**
- `MASSIVE_API_KEY` - read in `backend/app/market/factory.py`. Non-empty (after strip) selects `MassiveSource`; otherwise `SimulatorSource`.
- `MASSIVE_POLL_SECONDS` - read in `backend/app/market/factory.py`. Poll interval for Massive, default `15`.
- `OPENROUTER_API_KEY` - required for the AI chat. Specified in `planning/PLAN.md`; not read by any code yet.
- `LLM_MOCK` - `true` returns deterministic mock LLM replies. Specified in `planning/PLAN.md`; not implemented yet.

**Env file:**
- A root-level `.env` file exists (gitignored by the `.env` rule in `.gitignore`). It holds the environment configuration and was not read for this document.
- `.env.example` is referenced by `README.md` and `planning/PLAN.md` but is not present in the repository yet.
- The backend reads env vars from the process environment. Local runs use `uv run --env-file ../.env`. Docker runs are planned to use `--env-file .env`.

**Build / project config:**
- `backend/pyproject.toml` - project metadata, dependencies, dev group, pytest config
- `backend/uv.lock` - locked dependency graph
- `backend/.python-version` - `3.12`
- `.gitignore` - ignores `.env`, `.envrc`, `.venv`, `db.sqlite3`, and standard Python artifacts

**Database storage (planned):**
- SQLite, single file `db/finally.db` (volume-mounted at `/app/db` in the container). Not yet implemented: no `db/` directory and no `sqlite3` usage in the code. The stdlib `sqlite3` module is expected to be used, as no ORM is declared.

## Platform Requirements

**Development:**
- Python 3.12 and `uv` installed
- Run backend: `cd backend && uv sync && uv run --env-file ../.env uvicorn app.main:app --port 8000`
- Run tests: `cd backend && uv run pytest`
- Run price board: `uv run scripts/watch_prices.py [base_url]` (needs the server running on port 8000)
- Windows host is in use for this repository (PowerShell is the primary shell)

**Production:**
- Single Docker container on port 8000 (planned): Node 20 slim stage builds the Next.js export, Python 3.12 slim stage runs uvicorn and serves `/api/*` plus static files
- Deploy targets named in `planning/PLAN.md`: local Docker, AWS App Runner, Render, or any container platform

---

*Stack analysis: 2026-10-19*
