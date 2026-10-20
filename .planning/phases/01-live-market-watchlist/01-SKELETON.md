# Walking Skeleton: FinAlly (AI Trading Workstation)

**Phase:** 1
**Generated:** 2026-10-20

## Capability Proven End-to-End

A beginner runs one Docker image, opens the page served on port 8000, and sees a seeded watchlist stream live prices over SSE from SQLite-backed state, with an honest LIVE or SIMULATED badge. Plan 01-01 is the tracer: FastAPI serves the static Next.js export, a page reads `/api/stream/prices`, and the tickers come from SQLite.

## Architectural Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Framework (backend) | FastAPI 0.143 with the native `fastapi.sse` (`EventSourceResponse`, `ServerSentEvent`), run by uvicorn | Already used by the tested market layer; SSE is one-way push and needs no extra package (PLAN.md section 3) |
| Framework (frontend) | Next.js 16.4 App Router, `output: "export"`, `trailingSlash: true`, `images.unoptimized`; React 19.3; TypeScript strict | Static export lets FastAPI serve one origin on one port with no CORS (PLAN.md section 3) |
| Styling | Tailwind CSS 4.3, CSS-first `@theme` tokens in `frontend/src/app/globals.css` (no tailwind.config.js) | One source of colour; PLAN.md colours fixed as tokens (UI-01) |
| Client state | One zustand 5 store (`frontend/src/store/prices.ts`) fed by one hook-owned `EventSource`; components select primitives or stored references only | Avoids re-render storms at 2 Hz (research Pattern 10) |
| Data layer | stdlib `sqlite3`, no ORM; short-lived connections; `BEGIN IMMEDIATE` writes; `PRAGMA user_version` schema guard; seed gated on a new `users_profile` row | Single user, zero config; seed-once keeps removals removed (D-01, D-02) |
| Schema | All six PLAN.md tables created in Phase 1 (`trades.realized_pnl` nullable) with `user_id` default `"default"` | Later phases add behaviour, not migrations (D-01) |
| Wire contract | SSE envelope `{"prices": [PriceUpdate.to_dict()], "status": {"source": "live" or "simulated", "stale": bool, "note": str or null}}`, pushed when `(cache.version, stale)` changes | Frozen for the frontend and the E2E tests (D-03) |
| Market source | Startup probe picks Massive only on a real OK; otherwise the simulator with a plain-language, key-free note; never switched mid-session | Honest labelling (D-04, D-05, DATA-01, DATA-02) |
| Tracking | `backend/app/services/tracking.sync` is the only caller of `source.add_ticker` / `remove_ticker`; the tracked set is watchlist plus positions | One reconciler for the watchlist, trades (Phase 2) and AI actions (Phase 4) (D-13) |
| Ticker rule | `backend/app/tickers.normalize_ticker`: strip, ASCII only, upper-case, `^[A-Z]{1,5}(\.[A-Z])?$` | One rule for the watchlist, trade bar and AI chat (D-10) |
| Auth | None (single user, `user_id = "default"`); published on 127.0.0.1 only | PLAN.md: no login; localhost binding limits exposure |
| Deployment target | One multi-stage image: `node:24-slim` builds the export, `python:3.12-slim` plus uv runs uvicorn on port 8000; SQLite at `/app/db/finally.db` on a named volume | PLAN.md section 11 (Node 24 because Node 20 is end of life) |
| Directory layout | `backend/app/{market,db,services,routes}` (namespace packages except `market`), `backend/app/tickers.py`; `frontend/src/{app,components,hooks,store,shared}` (never `src/lib/`, which is gitignored) | Short modules; one concern per package |
| Tests | pytest (`backend/tests/market`, `backend/tests/db`, `backend/tests/test_*.py`); Vitest 5 in the node environment for pure frontend logic; a container gate script | Fast feedback per layer; the gate proves the real image |
| Ports | Docker app on 8000; local test servers and the phase container on 8020 | User preference |

## Stack Touched in Phase 1

- [x] Project scaffold: Next.js export build, uv backend, Vitest and pytest runners (plan 01-01)
- [x] Routing: `/api/stream/prices`, `/api/health`, `/api/watchlist` (GET, POST, DELETE), JSON 404 for unknown `/api/*`, and static `/` (plans 01-01, 01-02, 01-06)
- [x] Database: real read (watchlist at startup and GET) and real write (seed, add, remove) (plans 01-01, 01-06)
- [x] UI: add form and remove control wired to the API; live rows, badge and connection dot (plans 01-04 to 01-08)
- [x] Deployment: Docker build and run on a named volume, plus a smoke script and a container gate (plans 01-03, 01-08)

## Out of Scope (Deferred to Later Slices)

- Trading, positions, cash display, and the trade bar behaviour (Phase 2)
- Main chart content, heatmap, P&L chart, trade feedback, blotter, glossary (Phase 3)
- AI coach chat and LiteLLM integration (Phase 4)
- Start and stop scripts, Playwright E2E suite (Phase 5)
- Historical bars, multi-user, authentication, schema migrations

## Subsequent Slice Plan

Each later phase adds one vertical slice on top of this skeleton without changing its architectural decisions:

- Phase 2: Trading and live portfolio. One trade engine writes positions and trades and calls `tracking.sync`; the header shows cash and total value.
- Phase 3: See your profit. Feedback card, trade blotter, chart markers and glossary tooltips in the existing panels.
- Phase 4: AI coach. Structured-output chat that trades and edits the watchlist through the same engine and services.
- Phase 5: Ship it. Start and stop scripts, persistence across runs, and full automated test suites.
