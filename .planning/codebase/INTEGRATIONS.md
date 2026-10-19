---
last_mapped_commit: 24a4b2a30df1d0f61a24990f210bc270e83cd728
last_mapped_at: 2026-10-19
---
# External Integrations

**Analysis Date:** 2026-10-19

## APIs & External Services

**Market data (implemented, optional):**
- Massive (formerly Polygon.io) REST API - real US stock prices
  - Implementation: `backend/app/market/massive.py` (`MassiveSource`, `parse_snapshot`)
  - Base URL: `https://api.massive.com` (constant `BASE_URL`)
  - Endpoint: `GET /v2/snapshot/locale/us/markets/stocks/tickers` (constant `SNAPSHOT_PATH`), one request per poll for the union of tracked tickers
  - SDK/Client: none. Uses `httpx.AsyncClient` directly, with `Authorization: Bearer <key>` header and a 10 s timeout
  - Auth: env var `MASSIVE_API_KEY`
  - Poll interval: env var `MASSIVE_POLL_SECONDS` (default `15`, matching the free tier of 5 calls/min)
  - Selection: `backend/app/market/factory.py` (`create_market_source`). Used only when `MASSIVE_API_KEY` is non-empty after stripping whitespace.
  - Parsing: price falls back from `lastTrade.p` to `min.c` to `day.c` to `prevDay.c`. Entries without a usable price are skipped.

**Market data (default, no external calls):**
- Built-in GBM simulator - `backend/app/market/simulator.py` (`SimulatorSource`)
  - Ticks every `TICK_SECONDS = 0.5`
  - Seed prices, drift/volatility, and sector groups in `backend/app/market/seed_data.py`
  - Runs as an in-process asyncio task. No network access.

**LLM provider (planned, not implemented):**
- OpenRouter, accessed through LiteLLM
  - Model: `openrouter/nvidia/nemotron-3-super-120b-a12b:free`
  - Requirement: `provider.require_parameters: true` so only endpoints with Structured Outputs are used
  - Auth: env var `OPENROUTER_API_KEY`
  - Mock mode: `LLM_MOCK=true` returns deterministic replies with no network call (planned)
  - Usage in code: none yet. Specified in `planning/PLAN.md` section 9. The `openrouter` skill in `.claude/skills/openrouter/` documents the call pattern for agents.
  - Free model limit: 50 requests per day (`README.md`)

## Data Storage

**Databases:**
- SQLite (planned)
  - Location: `db/finally.db` at the repo root, volume-mounted to `/app/db` in Docker
  - Connection: no connection string or env var. The path is a fixed location chosen by the backend.
  - Client: not yet in code. The stdlib `sqlite3` module is the expected client.
  - Schema and seed data: planned in `backend/db/` (per `planning/PLAN.md`), not present yet.
  - Git status: `db/` directory is not yet created. `.gitignore` covers `db.sqlite3` only; `planning/PLAN.md` says `db/finally.db` should be gitignored.

**In-memory state (implemented):**
- Price cache - `backend/app/market/cache.py` (`PriceCache`). Holds latest price, previous price, and timestamp per ticker. Shared by the market source and the SSE stream. Lost on restart.

**File Storage:**
- Local filesystem only. No cloud object storage.

**Caching:**
- None external. The in-memory `PriceCache` is the only cache.

## Authentication & Identity

**Auth Provider:**
- None. The app is single-user with no login, by design (`planning/PLAN.md` section 2).
  - All tables carry a `user_id` column defaulting to `"default"` for future multi-user support.
- Outbound auth only: Bearer token to Massive (`MASSIVE_API_KEY`) and to OpenRouter (`OPENROUTER_API_KEY`, planned).

## Monitoring & Observability

**Error Tracking:**
- None detected

**Logs:**
- Python `logging` module. `backend/app/market/massive.py` creates `log = logging.getLogger(__name__)`. No handler or log configuration is set in `backend/app/main.py`.

## CI/CD & Deployment

**Hosting:**
- Planned: single Docker container on port 8000, run locally via `scripts/start_mac.sh` / `scripts/start_windows.ps1` (not yet present)
- Optional cloud targets named in `planning/PLAN.md`: AWS App Runner, Render. A Terraform config under `deploy/` is a stretch goal.

**CI Pipeline:**
- None detected. No `.github/workflows/` directory in the repository.

## Environment Configuration

**Required env vars:**
- `OPENROUTER_API_KEY` - required for AI chat (planned)

**Optional env vars:**
- `MASSIVE_API_KEY` - empty or absent selects the simulator (implemented)
- `MASSIVE_POLL_SECONDS` - Massive poll interval, default 15 (implemented)
- `LLM_MOCK` - `false` by default; `true` enables mock LLM replies (planned)

**Secrets location:**
- Root `.env` file (gitignored). Read by `uv run --env-file ../.env` for local backend runs and intended for `docker run --env-file .env` in production. Its contents were not read or recorded.
- `.env.example` is planned as the committed template and is not present yet.

## Webhooks & Callbacks

**Incoming:**
- None. The only inbound HTTP endpoints are:
  - `GET /api/health` - `backend/app/main.py`, returns `{"status": "ok"}`
  - `GET /api/stream/prices` - SSE stream, `backend/app/market/stream.py`, pushes every 0.5 s (`PUSH_SECONDS`), retry hint 1000 ms (`RETRY_MS`)

**Outgoing:**
- Massive REST snapshot polling (only when `MASSIVE_API_KEY` is set), see above
- OpenRouter chat completions (planned), see above
- No webhooks registered with any external service

**Planned API routes not yet implemented** (from `planning/PLAN.md` section 8): `/api/portfolio`, `/api/portfolio/trade`, `/api/portfolio/history`, `/api/watchlist` (GET/POST/DELETE), `/api/chat`.

---

*Integration audit: 2026-10-19*
