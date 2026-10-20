# Phase 1: Live Market Watchlist - Research

**Researched:** 2026-10-19
**Domain:** Walking skeleton for a FastAPI + SQLite + SSE + Next.js static-export app in one Docker image; hardening of an existing market-data layer (Massive probe, batched SSE, stale status)
**Confidence:** HIGH on what was executed this session (Next export, StaticFiles, Docker build, SQLite pattern, live Massive 401s, fastapi.sse source); MEDIUM on Massive 403/429 shapes (cannot be captured without a paid or free key)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Carried forward (roadmap / research, already locked)**
- **D-01:** Create the full PLAN.md §7 schema now, plus `trades.realized_pnl` (NULL for buys). Later phases must not need a migration. — **Reversibility:** one-way — changing it later needs a migration of the persisted volume DB.
- **D-02:** Seed the default user ($10,000) and the 10 default tickers only when the profile is brand-new. Removed tickers do not come back on restart.
- **D-03:** SSE envelope is frozen as one event per tick: `{prices: [...full snapshot...], status: {source, stale, note}}`. — **Reversibility:** costly — the frontend stores and E2E tests depend on this shape.
- **D-04:** The Massive key is probed once at startup with one real snapshot request. Only OK with prices means LIVE. Anything else (no key, not entitled, bad key, throttled, unreachable, empty) means SIMULATED with a plain-language reason that never includes the key. The source does not switch mid-session.
- **D-05:** `/api/health` returns status, active source, and fallback reason.
- **D-06:** Day %: previous close in LIVE mode. In SIMULATED mode it uses a session reference, labelled as such.
- **D-07:** DB code lives in `backend/app/db/`, not `backend/db/`, to avoid a collision with the `/app/db` volume. The runtime file is `db/finally.db`. `db/*.db*` is gitignored, and `.env.example` is committed.
- **D-08:** Market layer: harden only for the DATA-* items (cache version, batched stream, status/stale, probe, session day-% reference). No refactor.

**Page shell**
- **D-09:** Build the full terminal grid now: header, live watchlist, and empty placeholder panels for main chart, positions/heatmap, trade bar, and chat. Each placeholder carries a short label. Later phases fill the panels instead of reshuffling the layout.

**Adding tickers**
- **D-10:** Format check in both modes: uppercase-normalize, then `^[A-Z]{1,5}(\.[A-Z])?$`. Malformed input is rejected with a clear message.
- **D-11:** LIVE mode: also reject a well-formed symbol if Massive returns no price for it ("No market data for XYZ").
- **D-12:** SIMULATED mode: any well-formed symbol is accepted and gets a simulated price (uses the simulator's default params for unknown tickers).
- **D-13:** A newly added ticker starts streaming right away (`add_ticker` on the source). Removing it stops tracking it (positions do not exist yet in Phase 1).

**Status badge and STALE**
- **D-14:** The header badge reads LIVE or SIMULATED. The fallback reason or source note shows in a hover tooltip, not as inline text.
- **D-15:** STALE threshold is about 3 missed intervals: about 2s for the simulator, about 45s for Massive (3 x 15s poll). Prices frozen because the market is closed count as LIVE, not stale.
- **D-16:** When STALE: the badge turns amber and shows STALE, and watchlist prices dim. Rows are not hidden.
- **D-17:** Connection dot: green when connected, yellow while reconnecting, red when disconnected. It recovers on its own after a server restart.

**Watchlist rows**
- **D-18:** Columns: ticker, price, Day %, sparkline, with a remove "x" that shows on row hover.
- **D-19:** The flash covers the price cell only: green on uptick, red on downtick, fading in about 500ms via a CSS transition.
- **D-20:** Sparkline: inline SVG, a rolling buffer of the last ~2-3 minutes of ticks since page load (capped point count).
- **D-21:** Rows keep the order they were added (seed order, then additions at the end).

### Claude's Discretion
- Exact panel proportions, spacing, and placeholder wording within the Bloomberg-style dark theme (UI-01 colors fixed).
- Exact sparkline point cap and the stale threshold constants (within the ranges above).
- Wording of the plain-language fallback reasons and the error messages.

### Deferred Ideas (OUT OF SCOPE)
None. The discussion stayed within the phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DATA-01 | Startup probes Massive key with one real snapshot request; only OK with prices enables real data | "Massive probe" pattern; live 401 capture; `MassiveSource(client=...)` injection point already exists |
| DATA-02 | Any non-OK probe falls back to simulator with plain-language reason (never the key) | Outcome-to-reason table; reasons are fixed strings, never `str(exc)` |
| DATA-03 | Header badge LIVE/SIMULATED, reason on hover | Status envelope `status.source` + `status.note`; `Badge` component spec |
| DATA-04 | STALE indicator when source misses its interval | `last_ok` + `stale_after` on sources; stale is part of the SSE push key |
| DATA-05 | Day % true previous close (LIVE) / session reference labelled (SIMULATED) | Simulator already seeds `prev_close = seed price` (read `simulator.py:58-61`); label by `status.source` |
| DATA-06 | One batched SSE event per update with all prices plus status | `cache.version` gating; `ServerSentEvent(data=envelope)`; `raw_data` verified as the pre-serialized alternative |
| DATA-08 | `GET /api/health` reports status, source, fallback reason | Reuse the same status builder as the SSE envelope so they cannot disagree |
| DB-01 | SQLite created and seeded automatically on first start | `db/connection.py` init + seed; pattern executed in a spike |
| DB-02 | Default watchlist seeded only on brand-new profile | Seed gated on `INSERT OR IGNORE ... rowcount == 1`; executed in spike |
| DB-05 | DB files gitignored; committed `.env.example` | `.gitignore` gaps confirmed with `git check-ignore`; list of rules to add |
| WATCH-01 | Watchlist with ticker, price, Day %, sparkline since page load | Zustand price store, windowed history buffer, inline SVG sparkline |
| WATCH-02 | Green/red flash fading ~500ms | `PriceCell` with CSS transition via ref (D-19 literal); direction comes from `PriceUpdate.direction` |
| WATCH-03 | Add ticker; invalid symbols rejected with clear message | Regex gate + `check_ticker` on the source (LIVE: one snapshot request); 400/409 with `detail` |
| WATCH-04 | Remove ticker | `DELETE /api/watchlist/{ticker}` then `tracking.sync`; rowid ordering keeps D-21 |
| UI-01 | Bloomberg-style dark theme, UI-01 colors | Tailwind 4 `@theme` tokens; verified that `@theme` colors compile into the export CSS |
| UI-03 | Connection dot green/yellow/red, self-recovering | `usePriceStream` state machine (EventSource spec cited); red needs a timer because the browser keeps retrying |
| OPS-01 | Single multi-stage image serves frontend and API on 8000 | Dockerfile built and run in this session; `.dockerignore` required |
</phase_requirements>

## Summary

Phase 1 is a walking skeleton over a finished, tested market layer (54 tests pass today). Five things need building: (1) a `backend/app/db/` package that creates the full PLAN.md schema plus `trades.realized_pnl` and seeds only a brand-new profile; (2) DATA-* hardening of the market layer (cache version, source `kind`/`last_ok`, a startup probe with fallback reason, batched SSE envelope with status); (3) watchlist service and routes, with a `tracking.sync` reconciler, extended `/api/health`, a JSON 404 for unknown `/api/*`, and a static mount last; (4) a minimal Next.js static-export page with the full terminal grid, live watchlist, header badge, STALE and connection dot; (5) a multi-stage Dockerfile. Every high-risk mechanic of that list was executed in a scratchpad spike this session and works on this machine: Next 16.4.2 + Tailwind 4.3.3 + TS 6.0.3 export (also in a path with spaces), FastAPI `StaticFiles(html=True)` serving it with a JSON catch-all for `/api/*`, a Docker build of the full multi-stage file (38 s) with `/`, `/api/health` and the SSE stream answering and `docker stop` taking 0.7 s, and the SQLite init/seed/transaction pattern on Python 3.12.

Three findings change the plan versus the earlier research. First, the repo `.gitignore` has an unanchored `lib/` rule (line 17) that silently ignores `frontend/src/lib/` (confirmed with `git check-ignore`), and Tailwind v4 also skips gitignored files when scanning for classes; do not create a `lib` directory (use `frontend/src/shared/`). Second, this machine already has a Docker volume `finally-data` containing a `finally.db` from an earlier build of this app whose `trades` table lacks `realized_pnl`; `CREATE TABLE IF NOT EXISTS` would silently keep that old schema, so the init needs a `PRAGMA user_version` guard and verification must use a fresh volume name or a user decision about the old volume. Third, the SSE research flag is resolved from the installed FastAPI source: `ServerSentEvent(raw_data=<str>)` sends a pre-serialized string untouched, while `data=` is always `json.dumps(jsonable_encoder(...))`; at 10 tickers `data=envelope_dict` is fine and keeps tests simple.

**Primary recommendation:** Build bottom-up in this order: gitignore/.env.example/.dockerignore, then `app/db` with tests, then market hardening (`cache.version`, status, probe, batched stream, updated tests), then watchlist API plus lifespan wiring plus static mount, then the frontend skeleton, then the Dockerfile and a scripted container smoke test on port 8020 with a deliberately bad `MASSIVE_API_KEY` to prove the fallback badge path end to end.

## Project Constraints (from CLAUDE.md)

Extracted from `D:/Projects - AI Coder/Day14/finally/CLAUDE.md`, `.claude/CLAUDE.md` and the user's global CLAUDE.md. Treated as locked.

- Python only through `uv` (`uv run ...`, `uv add ...`); never `pip` or bare `python3`.
- Simple, incremental, short modules and functions; no over-engineering; no defensive programming; exception handling only at real boundaries (network, external JSON). No try/except around internal calls.
- Use latest library APIs. No emojis in code, logs or print statements. Docstrings short and clear; comments sparing.
- Modern typing only: `list[str]`, `dict[str, float]`, `X | None`; never `typing.Optional/List/Dict`. Annotate public signatures and return types; tests are not annotated.
- Inside `app.market` use relative imports; code outside uses absolute `from app.market import ...`. `app/market/__init__.py` is the only barrel. Do not create barrels elsewhere.
- Logging: module-level `log = logging.getLogger(__name__)`, `%s` lazy formatting, `log.warning` for recoverable external failures, no `print` in library code.
- Value objects are `@dataclass(frozen=True, slots=True)`. Env vars are read in one place per concern with `os.getenv` and an explicit default; strip whitespace on secrets.
- Tests mirror source: `backend/tests/<pkg>/test_<module>.py`. pytest config lives in `backend/pyproject.toml` (`asyncio_mode = "auto"`, `pythonpath = ["."]`).
- Do not introduce a linter or formatter config in this phase.
- Secrets: `.env` is never read into agent context; keys only via environment (`uv run --env-file ../.env`, Docker `--env-file`).
- Ports: app in Docker on 8000; local test servers on 8020. Windows host, PowerShell primary shell.
- Git: the user commits code; `.planning/` docs are not committed (`commit_docs: false`). Research was therefore not committed.
- Tailwind v4 CSS-first style only (`@import "tailwindcss"` plus `@theme`); no `tailwind.config.js`.
- Work through a GSD command before editing files (planner/executor concern, not this agent's).

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Price generation (simulator / Massive poll) | API / Backend (background task) | — | One process-wide producer writes the in-memory cache; frontend never talks to Massive |
| Massive key probe and fallback reason | API / Backend (lifespan) | — | Secret stays server-side; result is exposed as `status.source/note` and `/api/health` |
| Batched price stream and stale flag | API / Backend (SSE route) | Browser (renders STALE) | Server owns "is the feed fresh"; client only displays it |
| Watchlist persistence and ordering | Database / Storage | API / Backend | `watchlist` table, ordered by `rowid`; routes are thin |
| Ticker validation (format, LIVE existence) | API / Backend | — | Must run before any source or DB sees the string; client may pre-check but server is authoritative |
| Tracked-ticker reconciliation (watchlist ∪ positions) | API / Backend (`services/tracking.py`) | Database | Only `tracking.sync` calls `add_ticker`/`remove_ticker` |
| Sparkline history, flash, connection dot | Browser / Client | — | Pure client state accumulated from SSE since page load |
| Row order in the watchlist UI | Browser / Client (from REST list) | API | Join REST ticker order with SSE prices; stream also carries non-watchlist tickers in later phases |
| Static page serving | API / Backend (`StaticFiles`, mounted last) | CDN / Static (n/a) | Single origin, single port |
| Schema and seed | Database / Storage | API (lifespan triggers it) | Init in lifespan, not lazily on first request |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| next | 16.4.2 | App Router, `output: "export"` | [VERIFIED: npm registry] `npm view next version` = 16.4.2, engines `node >=20.9.0`; export build executed in spike |
| react / react-dom | 19.3.1 | UI | [VERIFIED: npm registry] required by Next 16 |
| typescript | ~6.0.3 | Types | [VERIFIED: npm registry] registry `latest` is now 7.0.2; spike used `~6.0.3` and `next build` plus `tsc --noEmit` passed. Stay on 6.0.x (TS 7 is CLI-only in Next 16.4 per STACK.md) |
| tailwindcss + @tailwindcss/postcss | 4.3.3 (both, same version) | Styling, dark theme | [VERIFIED: npm registry]; `@theme` token `--color-accent:#ecad0a` and utilities `bg-bg`, `text-accent` were found in the built CSS in spike |
| postcss | ^8.5 (resolves 8.5.31) | Tailwind integration | [VERIFIED: npm registry] |
| zustand | 5.0.15 | Stream-fed store | [VERIFIED: npm registry]; installed in spike, builds under static export |
| fastapi | 0.143.1 (locked) | API, SSE, static files | [VERIFIED: uv run python -c ...] `1.8.0 0.143.1` printed for starlette and fastapi |
| sqlite3 (stdlib) | Python 3.12.15 | Persistence | [VERIFIED: uv run python] pattern executed in spike |
| pydantic | >=2.14.1 (already locked transitively) | Request models | Declare explicitly with `uv add pydantic`; it is already installed |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| vitest | 5.0.5 | Frontend pure-logic tests (sparkline buffer, connection state, label helpers) | [VERIFIED: executed] `npx vitest run` passed a node-environment test in spike; pulls vite 8.3.4 itself. No jsdom or Testing Library needed in Phase 1 (component tests are TEST-02, Phase 5) |
| @types/node | ^24 | Node typings | Match Docker `node:24-slim`, not registry latest 26.x |
| @types/react, @types/react-dom | 19.3.0 | React typings | [VERIFIED: npm registry] |
| httpx | >=0.28.1 (locked) | Already a dependency; used by probe and by `MockTransport` tests | Existing |
| uv (Docker) | 0.12.23 image tag | `uv sync --locked --no-dev` in the image | [VERIFIED: docker manifest inspect] `ghcr.io/astral-sh/uv:0.12.23` exists |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `data=envelope_dict` in `ServerSentEvent` | `raw_data=json.dumps(...)` | `raw_data` skips `jsonable_encoder` and lets you build the payload once per tick for all clients; unnecessary at 10 tickers and tests would need `json.loads(e.raw_data)`. Keep `data=` |
| Short-lived `sqlite3.connect` per call | One shared connection (ARCHITECTURE.md Pattern 2) | SUMMARY.md resolved this in favour of short-lived connections; follow SUMMARY.md |
| Default (DELETE) journal mode | WAL | Spike showed only `finally.db` is created in default mode; WAL adds `-wal`/`-shm` files and gives nothing for a single-process, single-thread writer. Discretion; PITFALLS.md allows either on a named volume |
| `frontend/src/lib/` | `frontend/src/shared/` | `lib/` is gitignored (see Pitfall 1) |

**Installation:**
```bash
# Backend (from backend/)
uv add pydantic

# Frontend (from frontend/), exact versions as verified
npm install next@16.4.2 react@19.3.1 react-dom@19.3.1 zustand@5.0.15
npm install -D typescript@~6.0.3 @types/node@^24 @types/react@19.3.0 @types/react-dom@19.3.0 \
  tailwindcss@4.3.3 @tailwindcss/postcss@4.3.3 postcss@^8.5 vitest@5.0.5
```
Commit `frontend/package-lock.json`; the Dockerfile runs `npm ci`.

**Version verification:** ran `npm view <pkg> version` for next 16.4.2, react 19.3.1, react-dom 19.3.1, typescript 7.0.2 (do not use), tailwindcss 4.3.3, @tailwindcss/postcss 4.3.3, postcss 8.5.31, zustand 5.0.15, @types/node 26.6.5 (use ^24), @types/react 19.3.0, @types/react-dom 19.3.0, vitest 5.0.5 on 2026-10-19. `next` has no `postinstall` script.

## Package Legitimacy Audit

Run with `gsd-tools query package-legitimacy check`. The four SUS verdicts below have a single reason, `too-new`: each is the latest patch release of a very widely used package (tens of millions of weekly downloads, official source repos, `postinstall: null`). The planner should still insert one `checkpoint:human-verify` before the first `npm install` (review `package-lock.json` diff), per protocol.

| Package | Registry | Age (latest release) | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| next | npm | 2026-10-15 | 41M/wk | github.com/vercel/next.js | SUS (too-new) | Flagged: single install checkpoint |
| react | npm | 2026-10-14 | 116M/wk | github.com/react/react | SUS (too-new) | Flagged: single install checkpoint |
| react-dom | npm | 2026-10-14 | 109M/wk | github.com/react/react | SUS (too-new) | Flagged: single install checkpoint |
| postcss | npm | 2026-10-18 | 188M/wk | github.com/postcss/postcss | SUS (too-new) | Flagged: single install checkpoint |
| @types/node | npm | recent | 276M/wk | DefinitelyTyped | SUS (too-new) | Flagged: single install checkpoint |
| vitest | npm | recent | 77M/wk | vitest-dev/vitest | SUS (too-new) | Flagged: single install checkpoint |
| typescript | npm | 2026-07-08 | 184M/wk | github.com/microsoft/TypeScript | OK | Approved |
| tailwindcss | npm | 2026-07-16 | 84M/wk | github.com/tailwindlabs/tailwindcss | OK | Approved |
| @tailwindcss/postcss | npm | 2026-07-16 | 28M/wk | github.com/tailwindlabs/tailwindcss | OK | Approved |
| zustand | npm | 2026-08-13 | 37M/wk | github.com/pmndrs/zustand | OK | Approved |
| @types/react | npm | — | 106M/wk | DefinitelyTyped | OK | Approved |
| @types/react-dom | npm | — | 91M/wk | DefinitelyTyped | OK | Approved |
| pydantic | PyPI | 2026-10-11 | unknown | github.com/pydantic/pydantic | SUS (too-new, unknown-downloads) | Flagged; already in `uv.lock` as a FastAPI dependency, so `uv add pydantic` adds a constraint only |

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** next, react, react-dom, postcss, @types/node, vitest, pydantic (all `too-new` only; planner inserts one human-verify checkpoint covering the batch)

All names above come from the project's own STACK.md plus official Next/Tailwind documentation and were confirmed on the correct registry (npm for JS, PyPI for pydantic). No package was discovered through web search.

## Architecture Patterns

### System Architecture Diagram

```
                       startup (lifespan)
 .env / env vars ──► config.py (DB_PATH, STATIC_DIR) ─────────────┐
        │                                                         ▼
        │   init_db(DB_PATH): schema IF NOT EXISTS + user_version guard
        │        └─ seed 10 tickers only if profile row was just inserted
        │                                   │
        ▼                                   ▼
 start_market_source(cache, tickers_from_db)
   key set? ──no──► SimulatorSource (note: "No Massive API key set ...")
      │yes
      ▼
   probe: 1 GET snapshot?tickers=AAPL (5 s timeout)
      ├─ 200 + prices ──► MassiveSource(client reused) ──► LIVE
      └─ 401 / 403 / 429 / timeout / empty / bad body ──► SimulatorSource + fixed reason string
                         │
                         ▼
                 PriceCache (version++ on update/remove) ◄── source task (0.5 s sim | 15 s Massive)
                         │ last_ok / stale_after on source
                         ▼
 Browser ◄── SSE GET /api/stream/prices:  retry:1000, then one event whenever (cache.version, stale) changes
   EventSource            data: {"prices":[...full snapshot...],"status":{"source","stale","note"}}
      │  usePriceStream (zustand): prices, windowed history, status, connection state
      ▼
 Header (badge, dot, STALE) · Watchlist rows (PriceCell flash, Day %, Sparkline, x)  · placeholder panels
      │ add / remove
      ▼
 POST /api/watchlist {ticker} ─► normalize + regex ─► 409 if present ─► await source.check_ticker (LIVE: 1 snapshot call)
                                  ─► DB insert (BEGIN IMMEDIATE) ─► tracking.sync ─► source.add_ticker ─► return list
 DELETE /api/watchlist/{ticker} ─► DB delete ─► tracking.sync ─► source.remove_ticker (cache.remove, version++) ─► return list
 GET /api/health ─► {"status":"ok", source, stale, note}  (same status builder as SSE)
 /api/{anything else} ─► JSON 404          / and /_next/* ─► StaticFiles(html=True), mounted LAST
```

### Recommended Project Structure

```
backend/app/
├── main.py            # lifespan wiring, routers, JSON 404, static mount last
├── config.py          # DB_PATH, STATIC_DIR (env with Path(__file__)-based defaults)
├── context.py         # frozen Context(db_path, cache, source, market_note); get_ctx(request)
├── schemas.py         # normalize_ticker, WatchlistAdd
├── db/                # NOT backend/db (D-07)
│   ├── schema.sql     # all 6 tables + trades.realized_pnl
│   ├── connection.py  # connect, transaction, init_db (guard + seed)
│   └── watchlist.py   # SQL only: list_tickers, insert, delete, exists
├── services/
│   ├── tracking.py    # tracked_tickers(db_path), sync(ctx)
│   └── watchlist.py   # add / remove / list with validation and sync
├── routes/
│   ├── watchlist.py
│   └── system.py      # /api/health
└── market/            # existing; additions listed below
    ├── status.py      # build_status(source, note, now) -> dict
    ├── cache.py       # + version
    ├── factory.py     # + start_market_source (probe + fallback); create_market_source kept for tests
    ├── massive.py     # + probe_massive, last_ok, check_ticker, kind
    ├── simulator.py   # + kind, last_ok, check_ticker
    ├── interface.py   # + kind, last_ok, stale_after, non-abstract check_ticker default
    └── stream.py      # batched envelope
frontend/
├── next.config.ts  postcss.config.mjs  tsconfig.json (strict: true)  package.json  vitest.config.mts
└── src/
    ├── app/           # layout.tsx, page.tsx, globals.css (@theme)
    ├── shared/        # types.ts, api.ts, history.ts, format.ts   (NOT lib/)
    ├── store/         # prices.ts (zustand)
    ├── hooks/         # usePriceStream.ts
    └── components/    # Header, Badge, ConnectionDot, Watchlist, WatchlistRow, PriceCell, Sparkline, AddTicker, Panel
Dockerfile  .dockerignore  .env.example  db/.gitkeep
```

### Pattern 1: Version-gated batched SSE envelope (D-03, DATA-06)

**What:** `PriceCache` gets an integer `version` incremented in `update` and `remove`. The generator yields one `ServerSentEvent(data=envelope)` whenever `(cache.version, stale)` differs from the last sent key; the first event is always sent (so an empty cache still delivers `status`). The first-yielded `ServerSentEvent(retry=RETRY_MS)` is kept.

Existing values (read this session):
- [VERIFIED: backend/app/market/stream.py:12-13] `PUSH_SECONDS = 0.5` and `RETRY_MS = 1000`.
- [VERIFIED: backend/app/market/models.py:34-43] `to_dict` keys, quoted verbatim: `"ticker": self.ticker, "price": self.price, "previous_price": self.previous_price, "prev_close": self.prev_close, "change_pct": self.change_pct, "direction": self.direction, "timestamp": self.timestamp`. Reuse it inside `prices`.
- [VERIFIED: backend/app/market/simulator.py:68-79] `step()` has no `await`, so a batch built between ticks is always internally consistent.

Frozen wire shape (the `source` tokens are a planner decision, see Assumption A1):

```json
{"prices": [{"ticker": "AAPL", "price": 190.1, "previous_price": 190.0, "prev_close": 189.0,
             "change_pct": 0.582, "direction": "up", "timestamp": 1760000000.5}],
 "status": {"source": "simulated", "stale": false, "note": "No Massive API key set, using the built-in simulator."}}
```

```python
# stream.py (sketch). price_events takes a status callable so tests need no app.state.
async def price_events(cache, get_status, interval=PUSH_SECONDS):
    yield ServerSentEvent(retry=RETRY_MS)
    last_key = None
    while True:
        status = get_status()
        key = (cache.version, status["stale"])
        if key != last_key:
            last_key = key
            yield ServerSentEvent(data={"prices": [u.to_dict() for u in cache.all()], "status": status})
        await asyncio.sleep(interval)
```

**fastapi.sse research flag, resolved.** [VERIFIED: backend/.venv/Lib/site-packages/fastapi/sse.py:83-96] `raw_data: Annotated[str | None, Doc(...)] = None` with doc text "Raw string to send as the `data:` field **without** JSON encoding." and "Mutually exclusive with `data`." [VERIFIED: fastapi/sse.py:148-156] setting both raises `ValueError`. [VERIFIED: fastapi/routing.py:551-557] `if item.raw_data is not None: data_str = item.raw_data` / `elif item.data is not None:` ... `data_str = json.dumps(jsonable_encoder(item.data))`. So `data=` dicts are JSON-encoded per client per event; `raw_data=` is passed through. `format_sse_event` splits `data_str` on newlines into multiple `data:` lines [VERIFIED: fastapi/sse.py:221-223], so compact `json.dumps` (no newlines) stays one line. [VERIFIED: fastapi/sse.py:241] `_PING_INTERVAL: float = 15.0` keep-alive pings are inserted when the generator is idle (routing.py:610-621); important for Massive, whose version only changes every poll.

### Pattern 2: Source status and stale (DATA-04, D-15)

Add to each source: `kind` (`"simulated"` / `"live"`), `last_ok: float | None` (unix seconds), and a `stale_after` property: simulator 2.0 s (about 4 ticks), Massive `3 * poll_seconds` (45 s at the default 15). The simulator sets `last_ok` in `step()`; `MassiveSource.poll_once` sets it only when the parse returned at least one price for a tracked ticker (an empty or unusable body is a failed poll and must not refresh it). Frozen market-closed prices still come back from a successful poll, so they stay LIVE (D-15). One builder serves SSE and health:

```python
# market/status.py
def build_status(source, note, now=None) -> dict:
    now = time.time() if now is None else now
    stale = source.last_ok is None or now - source.last_ok > source.stale_after
    return {"source": source.kind, "stale": stale, "note": note}
```

`stale` is evaluated by the stream loop every 0.5 s, so the flip is pushed because stale is part of the push key. Do not set `last_ok` from `cache.update` timestamps (those are poll time, see PITFALLS Pitfall 3).

### Pattern 3: Massive probe and fallback (DATA-01/02, D-04)

`start_market_source(cache, tickers) -> tuple[MarketDataSource, str | None]` in `factory.py`; keep `create_market_source` untouched so the five tests in `test_factory.py` keep passing. Probe = one `GET SNAPSHOT_PATH` with `params={"tickers": "AAPL"}` and `timeout=5.0` on the client that `MassiveSource` will then reuse (the constructor already takes `client=`). Only 200 plus `parse_snapshot(...)` non-empty is LIVE; then `MassiveSource.start(tickers)` primes as it does today. Reasons are fixed strings, never `str(exc)`.

[VERIFIED: backend/app/market/massive.py:12-13] `BASE_URL = "https://api.massive.com"` and `SNAPSHOT_PATH = "/v2/snapshot/locale/us/markets/stocks/tickers"`. [VERIFIED: backend/app/market/massive.py:51-55] the client is built with `headers={"Authorization": f"Bearer {api_key}"}` and `timeout=10.0`, so the key never appears in a URL.

| Probe outcome | Condition | Evidence | Suggested reason text (discretion) |
|---|---|---|---|
| ok | 200 and `parse_snapshot` non-empty | Docs: snapshot returns `tickers[]` | (none; LIVE) |
| no key | env empty after strip | existing factory behaviour | "No Massive API key set, using the built-in simulator." |
| bad key | 401 | [VERIFIED: live curl 2026-10-19] bogus Bearer: `HTTP/1.1 401 Unauthorized` body `{"status":"ERROR","request_id":"...","error":"Unknown API Key"}`; no auth: 401 body `{"status":"ERROR",...,"error":"API Key was not provided"}` | "Massive rejected the API key, using the simulator." |
| not entitled | 403 | [ASSUMED] Polygon heritage; docs state no codes (WebFetch of the snapshot page: "The page doesn't document HTTP status codes or error responses") | "Your Massive plan does not include live prices (the free plan is end-of-day only), using the simulator." |
| throttled | 429 | [ASSUMED] | "Massive is rate limiting this key right now, using the simulator." |
| empty | 200 but no prices, or body not JSON | docs: snapshot is cleared daily at 3:30 AM EST | "Massive returned no prices, using the simulator." |
| unreachable | `httpx.TimeoutException` / other `httpx.HTTPError` | standard httpx | "Could not reach Massive (no network?), using the simulator." |
| other | any other status | — | "Massive returned an unexpected answer (HTTP <code>), using the simulator." |

Because every non-OK path falls back identically, a wrong guess about 403/429 only changes the wording, not safety. Catch `httpx.HTTPError` and `ValueError` (bad JSON) narrowly at this real boundary; no broader try/except.

### Pattern 4: `check_ticker` for add validation (D-11, D-12)

Add a non-abstract `async def check_ticker(self, ticker: str) -> bool` to `MarketDataSource` defaulting to `True`. `SimulatorSource` inherits that (D-12: any well-formed symbol is accepted; [VERIFIED: simulator.py:58-61] `_seed` uses `SEED_PRICES.get(ticker) or round(self.rng.uniform(50, 300), 2)` and [VERIFIED: simulator.py:73] `GBM_PARAMS.get(ticker, DEFAULT_PARAMS)` for unknown tickers). `MassiveSource.check_ticker` does one single-ticker snapshot request and returns whether `parse_snapshot` yields that ticker (writes nothing to the cache; `add_ticker` plus the next poll, at most 15 s later, fills the row, or have the watchlist service call it before insert and let the row show a dash until then). Service order: normalize and regex, duplicate check, `check_ticker`, DB insert, `tracking.sync`. Network failure inside `check_ticker` returns `False` and the service replies with a distinct message so "no data" and "cannot reach" are not conflated.

### Pattern 5: SQLite init, seed, transaction (DB-01, DB-02, D-01, D-02) - executed in spike

Executed on Python 3.12.15: short-lived `connect(path)` with `isolation_level=None`, `foreign_keys=ON`, `busy_timeout=5000`; a `transaction(path)` context manager issuing `BEGIN IMMEDIATE` / `COMMIT` / `ROLLBACK`; seed gated on `cursor.rowcount == 1` of `INSERT OR IGNORE INTO users_profile`. Spike output: first init `profile rowcount: 1`, after deleting MSFT and adding PYPL a second init printed `profile rowcount: 0`, final order `['AAPL','GOOGL','AMZN','TSLA','NVDA','META','JPM','V','NFLX','PYPL']` (MSFT did not return), duplicate insert raised `UNIQUE constraint failed: watchlist.user_id, watchlist.ticker`, and only `finally.db` existed in the directory. Notes:
- Do not call `executescript` inside the transaction (it commits implicitly). Split the schema into statements or run `executescript` once before `BEGIN`.
- Create the parent directory (`Path(path).parent.mkdir(parents=True, exist_ok=True)`); the container volume mount point already exists, local `db/` is created by `.gitkeep` or mkdir.
- Order the watchlist `ORDER BY rowid` (D-21). The seed rows share one `added_at`, so ordering by `added_at` ties.
- Version guard (see Pitfall 2): `PRAGMA user_version` is 0 in the old volume DB and in a fresh DB; detect "tables exist but `user_version` is 0" before running the schema, fail fast with a clear message, then `PRAGMA user_version = 1` after a clean init.

Schema columns [VERIFIED: planning/PLAN.md §7, read this session]: `users_profile(id TEXT PK default "default", cash_balance REAL default 10000.0, created_at TEXT)`, `watchlist(id, user_id default "default", ticker, added_at, UNIQUE(user_id, ticker))`, `positions(id, user_id, ticker, quantity REAL, avg_cost REAL, updated_at, UNIQUE(user_id, ticker))`, `trades(id, user_id, ticker, side "buy"|"sell", quantity REAL, price REAL, executed_at)` plus `realized_pnl REAL` NULL (D-01), `portfolio_snapshots(id, user_id, total_value REAL, recorded_at)`, `chat_messages(id, user_id, role "user"|"assistant", content, actions TEXT, created_at)`. Add `CHECK (side IN ('buy','sell'))` and `CHECK (role IN ('user','assistant'))`.

### Pattern 6: Tracking reconciler (DATA-07 groundwork, D-13)

`services/tracking.py`: `tracked_tickers(db_path)` = `SELECT ticker FROM watchlist UNION SELECT ticker FROM positions` (the `positions` table exists, returns nothing in Phase 1) and `async sync(ctx)` comparing against `ctx.source.tickers` and calling `add_ticker`/`remove_ticker` for the differences. It is the only caller of those two methods. Lifespan starts the source with `sorted`/ordered tickers from the DB (resolves the `main.py` TODO). Do not mark DATA-07 complete (Phase 2 owns the positions side).

### Pattern 7: Serving the export (OPS-01) - executed in spike

Include all routers first, then a JSON catch-all, then the static mount last, only if the directory exists:

```python
# main.py tail
app.include_router(stream_router); app.include_router(watchlist_router); app.include_router(system_router)

@app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def api_not_found(path: str) -> JSONResponse:
    return JSONResponse({"detail": "Not found"}, status_code=404)

if STATIC_DIR.is_dir():
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
```

Spike results through `httpx.ASGITransport`: `/` 200 `text/html; charset=utf-8`; `/index.html` 200; `/api/health` 200 `application/json`; `/api/nope` 404 `application/json`; `/nope` 404 `text/html`; `/_next/static/chunks/*.js` 200 `text/javascript; charset=utf-8`; `/404.html` and `/_not-found/` 200 html. In Docker the same image answered `/` 200 `text/html`, `/api/health` `{"status":"ok"}`, and the SSE endpoint streamed `retry: 1000` then data lines.

### Pattern 8: `usePriceStream` and the connection dot (UI-03, D-17)

[CITED: html.spec.whatwg.org/multipage/server-sent-events.html] Non-200 or non-`text/event-stream` response: "fail the connection", readyState CLOSED, "it does not attempt to reconnect". Network error: "reestablish the connection", readyState CONNECTING, an `error` event fires, and the client waits the reconnection time (default implementation-defined; the `retry:` field sets it, and the server sends `retry: 1000`). Consequence: while the server is down the browser stays in CONNECTING and keeps retrying, so a plain `readyState` mapping would never show red. Prescribed state machine:

- `onopen` -> `connected` (green), clear the timer.
- `onerror` with `readyState === EventSource.CONNECTING` -> `reconnecting` (yellow); start a one-shot timer (about 5 s) that sets `disconnected` (red) if no `onopen` happened meanwhile. The browser keeps retrying by itself, `onopen` turns it green again.
- `onerror` with `readyState === EventSource.CLOSED` -> `disconnected` (red) and re-create the EventSource with capped backoff (1 s, 2 s, 5 s).
- Create the `EventSource` only inside `useEffect` and `close()` it in cleanup (React Strict Mode double-mount, and `new EventSource` at module scope would break `next build` prerender).
- Extract the transition logic as a pure function so Vitest can test it without a DOM.

### Pattern 9: Flash cell per D-19 (WATCH-02)

D-19 locks "CSS transition", so use a transition (not a keyframes animation). Per cell: `useLayoutEffect` keyed on `p.timestamp`: set background to the flash colour with `transition: none`, force reflow (`void el.offsetWidth`), then set `transition: background-color 500ms ease-out` and background `transparent`. Skip when `direction === "flat"`. [VERIFIED: models.py:20-25] `direction` returns `"up"`, `"down"` or `"flat"`. The simulator rounds to cents (`round(price, 2)`, simulator.py:79) so many ticks are `"flat"` and correctly do not flash. Hold no flash state in React state.

### Pattern 10: Zustand store (WATCH-01)

[VERIFIED: frontend spike `node_modules/zustand/esm/react.mjs:5-9`] `useStore` passes `selector(api.getState())` straight to `useSyncExternalStore` as the snapshot. A selector that returns a fresh object or array each call (`s => ({a: s.a})`, `s => s.rows.filter(...)`) therefore re-renders endlessly. Select primitives or already-stored references (`s => s.prices[ticker]`, `s => s.status.source`), derive lists in the component with `useMemo`. Store shape: `prices: Record<string, PriceUpdate>`, `history: Record<string, [number, number][]>`, `status: MarketStatus | null`, `connection: "connected" | "reconnecting" | "disconnected"`, `tickers: string[]` (REST order). History: append `[timestamp, price]` only when the timestamp differs from the last point; trim points older than 180 s and cap at 400 (D-20: about 2-3 minutes, capped count); drop history for tickers no longer in the batch. Rows come from the REST ticker list joined with `prices`, so a row exists (price shown as a dash) before its first price arrives and non-watchlist tickers streamed in later phases never appear.

### Anti-Patterns to Avoid
- **Per-ticker SSE events or per-client `last_sent` dicts:** replaced by the full-snapshot envelope; fixes "removed tickers silently dropped" (CONCERNS.md).
- **Calling `source.add_ticker/remove_ticker` from routes:** go through `tracking.sync` only.
- **Static mount registered before routers:** it would swallow `/api/*` and SSE.
- **Setting `last_ok` from cache timestamps or on empty polls:** makes stale undetectable.
- **Lazy DB init on first request:** init in lifespan; two first requests would race on create and seed.
- **`str(exc)` in a user-facing reason:** fixed strings only.
- **Creating `frontend/src/lib/`:** gitignored and invisible to Tailwind class scanning.
- **`data=` and `raw_data=` on the same event:** raises `ValueError` (fastapi/sse.py:148-156).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| SSE framing, keep-alive, buffering headers | Custom `StreamingResponse` | `EventSourceResponse` + `ServerSentEvent` (already used) | Sets `Cache-Control: no-cache`, `X-Accel-Buffering: no`, 15 s ping [VERIFIED: fastapi/routing.py:664-666] |
| Static file serving of the export | Custom catch-all route reading files | `StaticFiles(directory, html=True)` | Verified serving `/`, `/_next/*`, `404.html` with correct content types |
| Tailwind theme tokens | `tailwind.config.js` | `@theme { --color-* }` in `globals.css` | v4 CSS-first; verified compiled in spike |
| Stream-fed shared state | React Context per tick | zustand with primitive selectors | Context re-renders the whole tree twice a second |
| Sparklines | Per-row chart instances | Inline SVG `<polyline>` from the windowed buffer | D-20; 10 tiny charts at 2 Hz is overkill |
| Connection retry loop for the happy path | Own reconnect logic | `EventSource` built-in retry plus a timer and a CLOSED fallback | Browser already retries network errors |
| Atomic seed | Check-then-insert in Python | `INSERT OR IGNORE` + `rowcount` inside one `BEGIN IMMEDIATE` | No race, no half-seeded DB |
| Ticker format checks scattered across layers | Ad-hoc `.upper()` calls | One `normalize_ticker()` in `schemas.py` used by routes (and later chat) | PITFALLS Pitfall 26 |

**Key insight:** every hard piece here (SSE framing, static serving, atomic seed, EventSource retry) already exists in the stack; the work is wiring plus a small number of status and probe rules.

## Runtime State Inventory

Not a rename or refactor phase, but one runtime-state hazard was found on this machine and is recorded here because it directly affects D-01.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | Docker named volume `finally-data` exists and holds `/d/finally.db` (94,208 bytes, mtime Oct 19 18:35). [VERIFIED: read-only `docker run --rm -v finally-data:/d:ro ... sqlite_master`] its `trades` table is `CREATE TABLE trades ( id TEXT PRIMARY KEY, user_id TEXT NOT NULL DEFAULT 'default', ticker TEXT NOT NULL, side TEXT NOT NULL, quantity REAL NOT NULL, price REAL NOT NULL, executed_at TEXT NOT NULL )` with no `realized_pnl`; the other five tables match PLAN.md §7 | Data migration is NOT wanted (D-01). Add the `user_version` guard so init refuses a foreign-schema DB with a clear message, and verify Phase 1 with a fresh volume (for example `finally-p1-data`). Whether to delete `finally-data` is a user decision, not an agent action |
| Live service config | None - verified: no external service holds config for this app | none |
| OS-registered state | None - verified: `docker ps` shows no running containers; nothing scheduled | none |
| Secrets/env vars | `MASSIVE_API_KEY`, `MASSIVE_POLL_SECONDS`, `OPENROUTER_API_KEY`, `LLM_MOCK` in the gitignored root `.env` (not read, per project rule). `.env.example` does not exist yet [VERIFIED: `git check-ignore` reports it not ignored and `ls` shows no file] | Create `.env.example` with empty values; names only |
| Build artifacts | Docker image `finally:latest` (977 MB, created 2026-10-19T15:04 UTC, `Cmd ["uvicorn","app.main:app","--host","0.0.0.0","--port","8000"]`, `WorkingDir /app/backend`) from an earlier build already exists | Tag new builds explicitly (for example `finally:p1`) until the user agrees to overwrite `finally:latest` |

## Common Pitfalls

### Pitfall 1: `lib/` is gitignored, and Tailwind skips gitignored files
**What goes wrong:** `frontend/src/lib/api.ts` never shows up in `git status`, so the user's commit silently omits source files, and Tailwind classes that appear only in such files are not generated.
**Why it happens:** [VERIFIED: `git check-ignore -v frontend/src/lib/api.ts` output] `.gitignore:17:lib/	frontend/src/lib/api.ts`. The Python packaging block has an unanchored `lib/`. [CITED: tailwindcss.com/docs/detecting-classes-in-source-files] automatic detection ignores "Files that are in your `.gitignore` file".
**How to avoid:** Use `frontend/src/shared/` (verified not ignored along with `app/`, `components/`, `store/`, `hooks/`). Alternatively anchor the rule (`/lib/`, `/lib64/`), but avoiding the name needs no `.gitignore` edit.
**Warning signs:** a source directory that `git status` never lists; a utility class that works in `next dev` source but not in the built CSS.

### Pitfall 2: Reusing the old `finally-data` volume
**What goes wrong:** The app starts "successfully" against the old DB, the profile row exists so nothing is seeded, `trades.realized_pnl` is missing, and Phase 2 fails later on the first sell.
**Why it happens:** `CREATE TABLE IF NOT EXISTS` never alters an existing table; see Runtime State Inventory.
**How to avoid:** `PRAGMA user_version` guard (fresh DB: `users_profile` absent, so create and set version 1; existing DB with version 0 and tables present: raise `RuntimeError` naming the file and telling the user to remove the volume). Use a new volume name for Phase 1 verification.
**Warning signs:** `sqlite3.OperationalError: table trades has no column named realized_pnl`; watchlist differing from the 10 defaults on a "fresh" start.

### Pitfall 3: Existing tests that will break, and how to keep the rest green
**What goes wrong:** [VERIFIED: ran `cd backend && uv run pytest -q` -> "54 passed in 2.79s"] baseline is green; the batched envelope and DB-backed lifespan break specific tests.
**Will break:** all of `backend/tests/market/test_stream.py` (it asserts per-ticker events: `e.data["ticker"]`, `parse(...)["direction"]`, and the fixture sets `app.state.price_cache`), `test_app.py` (asserts `resp.json() == {"status": "ok"}` and `lifespan(app)` now needs a DB path and a probe). **Stays green if untouched:** `test_cache`, `test_simulator`, `test_massive`, `test_factory` (keep `create_market_source` as is; add `start_market_source` beside it).
**How to avoid:** a `conftest.py` fixture that sets `DB_PATH` to `tmp_path/"finally.db"` (and deletes `MASSIVE_API_KEY`) via `monkeypatch`; rewrite the stream tests against `price_events(cache, get_status, interval=0)`.

### Pitfall 4: Probe at startup blocks or burns the free budget
**What goes wrong:** startup waits up to 10 s per request (client timeout) and a restart loop adds probe plus priming each time.
**How to avoid:** pass `timeout=5.0` on the probe request; one probe request only; do not retry; free-plan keys fail at the probe (403) so they never reach the 5 calls/min poller.

### Pitfall 5: LIVE mode "stale" on a closed market or the 3:30 AM reset
**What goes wrong:** treating "no price change" as stale, or treating an empty body during the reset as healthy.
**How to avoid:** `last_ok` moves only on a poll that parsed at least one tracked ticker; a successful poll of frozen weekend data refreshes it (stays LIVE). [CITED: massive.com snapshot docs] "Snapshot data is cleared each day at 3:30 AM EST" and refills "as early as 4:00 AM EST", so expect a stale badge in that window.

### Pitfall 6: EventSource never shows red
**What goes wrong:** with the server down the browser stays CONNECTING (yellow) forever; success criterion 4 wants red when disconnected.
**How to avoid:** the timer rule in Pattern 8. Also handle CLOSED explicitly with a manual re-create.

### Pitfall 7: Next defaults and static-export traps
- `next build` writes `tsconfig.json` with `"strict": false` [VERIFIED: spike tsconfig]; set `"strict": true` explicitly.
- `output: "export"`, `trailingSlash: true`, `images: { unoptimized: true }`; no `rewrites`, dynamic routes, or `next/image` default loader. Build output is `frontend/out` containing `index.html`, `404.html`, `_next/`.
- Any component touching `EventSource`, `window` or `localStorage` must be `"use client"` and touch the API only in `useEffect`; verified building with an `EventSource` in an effect.
- Fonts: use the system monospace stack, not `next/font/google` (build-time network).
- `NEXT_PUBLIC_*` is build-time only; call `/api/...` relatively. Local loop: build the frontend, then run the backend on port 8020 with `STATIC_DIR` pointing at `frontend/out`; no CORS and no dev proxy needed.

### Pitfall 8: Docker build context and ownership
- A `.dockerignore` is mandatory: the repo has `backend/.venv` with about 12,500 files (Windows venv) that must not be copied. Spike used `**/node_modules`, `**/.next`, `**/out`, `**/.venv`, `**/__pycache__`; add `.git`, `.env`, `db/*.db*`, `.planning`.
- `npm ci` needs a committed `package-lock.json`; `uv sync --locked` needs the committed `uv.lock` and `backend/.python-version`.
- Run as root (no `USER`); a named volume mounted over `/app/db` is then writable. `RUN mkdir -p /app/db`.
- Use `ENV UV_PYTHON_DOWNLOADS=never` so uv uses the image's Python 3.12.
- Add `--timeout-graceful-shutdown 2` to the CMD (open SSE clients otherwise delay `docker stop`).

### Pitfall 9: Watchlist row order and re-add semantics
Order by `rowid`; removal then re-add moves a ticker to the end in both DB and cache, consistent with D-21. [VERIFIED: simulator.py:58-61] a re-added simulated ticker re-seeds at `SEED_PRICES` (CONCERNS.md accepted behaviour).

### Pitfall 10: Name collisions around "status"
`/api/health` already returns `{"status": "ok"}` [VERIFIED: backend/app/main.py:29-31]. Keep that key and add `source`, `stale`, `note` beside it (`{"status": "ok", **build_status(...)}`), so the existing key stays and the SSE `status` object is reused unchanged.

## Code Examples

### Existing `main.py` lifespan to replace (read this session)
```python
# [VERIFIED: backend/app/main.py:10-22]
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start the market data source on startup and stop it on shutdown.

    TODO: replace DEFAULT_TICKERS with watchlist UNION open positions from SQLite.
    """
    cache = PriceCache()
    source = create_market_source(cache)
    await source.start(DEFAULT_TICKERS)
```
Target lifespan: `init_db(DB_PATH)`; `tickers = tracked_tickers(DB_PATH)`; `source, note = await start_market_source(cache, tickers)`; store a frozen `Context`; `yield`; `await source.stop()`.

### Probe (sketch, matches the outcome table)
```python
# market/massive.py
async def probe_massive(client: httpx.AsyncClient) -> str | None:
    """Return None when Massive serves prices, else a plain-language reason."""
    try:
        resp = await client.get(SNAPSHOT_PATH, params={"tickers": "AAPL"}, timeout=5.0)
        if resp.status_code == 200:
            return None if parse_snapshot(resp.json()) else "Massive returned no prices, using the simulator."
    except httpx.TimeoutException:
        return "Massive did not answer in time, using the simulator."
    except httpx.HTTPError:
        return "Could not reach Massive (no network?), using the simulator."
    except ValueError:
        return "Massive sent an unreadable answer, using the simulator."
    return REASONS.get(resp.status_code, f"Massive returned HTTP {resp.status_code}, using the simulator.")
```

### Test pattern for the probe (reuses the existing MockTransport style)
```python
# [VERIFIED: backend/tests/market/test_massive.py:17-24] existing helper style
def make_source(handler, poll_seconds: float = 15.0):
    client = httpx.AsyncClient(
        base_url="https://api.massive.com",
        transport=httpx.MockTransport(handler),
        headers={"Authorization": "Bearer k"},
    )
```
Write one test per outcome in the table (200 ok, 200 empty, 401 with the captured body, 403, 429, `httpx.ConnectTimeout`, `httpx.ConnectError`, 200 with non-JSON) and assert the returned reason never contains the key string.

### Watchlist route contract (planner to confirm shapes)
`GET /api/watchlist` -> `[{"ticker": "AAPL", "price": 190.0}, {"ticker": "NEW", "price": null}]` in DB order. `POST /api/watchlist {"ticker": "pypl"}` -> 200 with the same list shape; 400 `{"detail": "..."}` for format or no-data; 409 `{"detail": "PYPL is already on your watchlist."}`. `DELETE /api/watchlist/{ticker}` -> 200 list, 404 if absent. Validate in the service (not with a Pydantic `pattern=`) so the client gets a readable `detail` string instead of FastAPI's default 422 error list.

### Frontend types mirroring the frozen envelope
```ts
// src/shared/types.ts (field names from PriceUpdate.to_dict, models.py:34-43)
export type PriceUpdate = {
  ticker: string; price: number; previous_price: number; prev_close: number;
  change_pct: number; direction: "up" | "down" | "flat"; timestamp: number;
};
export type MarketStatus = { source: "live" | "simulated"; stale: boolean; note: string | null };
export type PriceEnvelope = { prices: PriceUpdate[]; status: MarketStatus };
```

### Tailwind v4 theme (verified compiled)
```css
@import "tailwindcss";
@theme {
  --color-bg: #0d1117;        --color-panel: #161b22;   --color-border: #30363d;
  --color-accent: #ecad0a;    --color-primary: #209dd7; --color-submit: #753991;
  --color-up: #3fb950;        --color-down: #f85149;
}
```
[VERIFIED: spike build] `bg-bg`, `text-accent` and `--color-accent:#ecad0a` appear in the emitted CSS. UI-01 colours quoted verbatim from REQUIREMENTS.md: "amber `#ecad0a` accent, blue `#209dd7`, purple `#753991` submit buttons" (the Add ticker button is the only submit button in Phase 1).

### Dockerfile (built and run in this session; added `STATIC_DIR` mount in a spike `main.py`)
```dockerfile
FROM node:24-slim AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.12.23 /uv /usr/local/bin/uv
ENV UV_PYTHON_DOWNLOADS=never UV_LINK_MODE=copy UV_COMPILE_BYTECODE=1
WORKDIR /app/backend
COPY backend/pyproject.toml backend/uv.lock backend/.python-version ./
RUN uv sync --locked --no-dev
COPY backend/app ./app
COPY --from=frontend /frontend/out /app/static
RUN mkdir -p /app/db
ENV PATH="/app/backend/.venv/bin:$PATH" STATIC_DIR=/app/static DB_PATH=/app/db/finally.db
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--timeout-graceful-shutdown", "2"]
```
Spike result: image built in 38 s; container answered `/` 200 `text/html`, `/api/health` `{"status":"ok"}`, SSE `retry: 1000` then data; `docker stop` real 0.7 s. `rich` (dev group) is absent from this image, which is fine for the dev-only watch script.

### `.gitignore` and ancillary files to add (DB-05)
`git check-ignore` showed these planned paths are NOT ignored today: `db/finally.db`, `db/finally.db-wal`, `frontend/node_modules/a`, `frontend/out/index.html`. Add: `db/*.db`, `db/*.db-*`, `frontend/node_modules/`, `frontend/.next/`, `frontend/out/`, and keep `db/.gitkeep` tracked. `.env.example` is already not ignored (`.env` rule matches only that exact name); create it with names and empty values for `OPENROUTER_API_KEY`, `MASSIVE_API_KEY`, `LLM_MOCK` (values unquoted: Docker `--env-file` does not strip quotes), and `MASSIVE_POLL_SECONDS` if documented.

### Container smoke test (port 8020 per user preference; fake key proves the fallback path)
```bash
docker build -t finally:p1 .
docker run -d --name finally-p1 -p 127.0.0.1:8020:8000 -v finally-p1-data:/app/db \
  -e MASSIVE_API_KEY=notarealkey finally:p1
curl -s localhost:8020/api/health          # source "simulated", note says the key was rejected
curl -s -N -m 3 localhost:8020/api/stream/prices | head -3
curl -s -X POST localhost:8020/api/watchlist -H "content-type: application/json" -d '{"ticker":"pypl"}'
docker restart finally-p1                   # watchlist keeps PYPL; removed default stays removed
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Per-ticker SSE events with `last_sent` identity diffing | One full-snapshot envelope gated by `cache.version` | This phase (D-03) | Removed tickers vanish by themselves; no per-connection state |
| `fastapi.sse` JSON-only payloads | `ServerSentEvent.raw_data` for pre-serialized strings | FastAPI 0.143.x (present in locked version) | Optional optimisation only |
| Tailwind v3 config file | v4 `@import "tailwindcss"` + `@theme` | Tailwind 4 | No `tailwind.config.js`, no autoprefixer |
| Node 20 build stage (PLAN.md) | `node:24-slim` | Node 20 EOL 2026-04-30 (STACK.md) | Safe deviation; Next 16.4 supports >=20.9 |
| TypeScript 6 | TypeScript 7.0.2 now `latest` on npm | 2026 | Not adopted; Next 16.4 supports it only via the experimental CLI path (STACK.md) |

**Deprecated/outdated:**
- `chart.addAreaSeries()` / `series.setMarkers()` (Lightweight Charts v4): not used in Phase 1.
- Lazy DB init on first request: replaced by lifespan init.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `status.source` values are lowercase `"live"` / `"simulated"`, and `/api/health` reuses the same keys (`source`, `stale`, `note`) beside `status: "ok"`. CONTEXT D-03/D-05 name the keys but not the value tokens or the health key for the reason | Pattern 1, Pitfall 10 | Contract is "costly" to change (D-03); planner must freeze it explicitly. D-05 says "fallback reason", so the health key could be `reason` instead of `note` |
| A2 | Massive returns 403 for a free-plan key on the snapshot endpoint and 429 when throttled | Pattern 3 table | Only the wording of the reason changes; every non-200 falls back to the simulator |
| A3 | Massive omits unknown tickers from a 200 snapshot response (rather than erroring), so `check_ticker` sees "no price" | Pattern 4 | LIVE add of a bogus symbol might surface as an error status; `check_ticker` treats any non-OK as `False`, so the user message is still "No market data for XYZ" |
| A4 | Stale constants: simulator 2.0 s, Massive `3 * poll_seconds` | Pattern 2 | Cosmetic; within the D-15 ranges and Claude's discretion |
| A5 | Default journal mode (no WAL) is sufficient | Standard Stack alternatives | Low; WAL can be enabled later without a schema change |
| A6 | The old Docker volume `finally-data` and image `finally:latest` are disposable leftovers of an earlier build | Runtime State Inventory | Deleting or overwriting them would destroy the user's earlier data; agents must ask first |
| A7 | Starlette `StaticFiles` rejects path traversal outside the directory | Security Domain | Low; standard Starlette behaviour, add one test (`/..%2f..%2fetc/passwd` returns 404) |
| A8 | Component tests (jsdom, Testing Library) are not needed in Phase 1; pure-logic Vitest plus a human visual check at end of phase is enough | Validation Architecture | If the user wants automated flash coverage now, add jsdom and RTL (TEST-02 is Phase 5) |
| A9 | Chrome/Firefox keep `readyState` CONNECTING on connection-refused retries (spec text supports it; not observed in a real browser here) | Pattern 8 | If a browser went to CLOSED instead, the CLOSED branch (red plus manual re-create) still recovers |

## Open Questions

1. **What to do with the existing `finally-data` volume and `finally:latest` image?**
   - What we know: both exist; the volume DB lacks `trades.realized_pnl`; PLAN.md start scripts (Phase 5) use `finally-data`.
   - What's unclear: whether the old data matters to the user.
   - Recommendation: Phase 1 verification uses `finally-p1-data` and tag `finally:p1`; raise a human-decision checkpoint before Phase 5 on removing `finally-data` (`docker volume rm finally-data`).

2. **Massive 403 / 429 / free-plan response shapes.**
   - What we know: bad key and missing key are live-verified as 401 with the bodies quoted above; all non-OK fall back safely.
   - What's unclear: the exact 403/429 bodies; no key was available. The project `.env` was deliberately not read.
   - Recommendation: add an optional dev-only script `backend/scripts/capture_massive.py` (reads the key from the environment, prints status and body, never prints the key) and, if the user has a free or paid key, record one real response per plan as a test fixture. Not blocking.

3. **Should the free-plan reason mention the end-of-day alternative?**
   - What we know: EOD mode is out of scope (EXT-V2-03 deferred).
   - Recommendation: wording only; keep it short and plain.

4. **Duplicate add: 409 with message, or idempotent 200?**
   - Recommendation: 409 with "already on your watchlist" (gives the beginner feedback); within Claude's discretion on messages.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Docker Engine (Desktop, daemon running) | OPS-01 build and run | yes | 29.8.1 | — |
| Docker base images `node:24-slim`, `python:3.12-slim`, `ghcr.io/astral-sh/uv:0.12.23` | Dockerfile | yes | manifests exist; spike build succeeded | — |
| Node.js / npm (host) | `tsc`, `vitest`, local `next build` | yes | Node 26.2.0 / npm 11.13.0 (image uses Node 24) | Build in Docker only |
| uv | backend deps and tests | yes | 0.12.23 | — |
| Python 3.12 (backend venv) | pytest, uvicorn | yes | 3.12.15 | — |
| Network to `api.massive.com` | probe tests against the live API (optional) | yes | live curl returned 401 JSON | MockTransport tests |
| Massive API key (free or paid) | capturing 403/200 fixtures | unknown (`.env` not read) | — | Skip; probe falls back safely |
| Port 8020 free for local test servers | smoke tests | yes (no listeners found; `docker ps` empty) | — | pick another port |
| Browser for visual check | success criteria 1-5 (human verify) | user's machine | — | end-of-phase human-verify |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** Massive key (fixture capture deferred; mocked tests cover every branch).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Backend framework | pytest 9.1.1 + pytest-asyncio 1.4.0, `asyncio_mode = "auto"` [VERIFIED: backend/pyproject.toml:18-21] |
| Frontend framework | Vitest 5.0.5, node environment, pure-logic tests (Wave 0 install) |
| Config file | `backend/pyproject.toml`; `frontend/vitest.config.mts` (Wave 0) |
| Quick run command | `cd backend && uv run pytest -q` (54 tests in 2.79 s today) |
| Frontend quick run | `cd frontend && npx vitest run && npx tsc --noEmit` |
| Full suite command | `cd backend && uv run pytest -q` then `cd frontend && npm run build` then the container smoke script |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DATA-01 | Probe 200 with prices selects `MassiveSource` | unit (MockTransport) | `uv run pytest tests/market/test_probe.py -q` | Wave 0 |
| DATA-02 | 401/403/429/timeout/empty/bad body all fall back; reason never contains the key | unit | `uv run pytest tests/market/test_probe.py -q` | Wave 0 |
| DATA-03 | status carries `source` and `note`; badge label helper maps source to LIVE/SIMULATED | unit + Vitest | `uv run pytest tests/market/test_status.py -q`; `npx vitest run` | Wave 0 |
| DATA-04 | stale true after threshold with injected clock; stale flip pushes an event | unit | `uv run pytest tests/market/test_status.py tests/market/test_stream.py -q` | Wave 0 (stream tests rewritten) |
| DATA-05 | Simulator `prev_close` equals session start price; LIVE uses `prevDay.c` (existing `parse_snapshot` tests) | unit | `uv run pytest tests/market -q` | partial (existing) |
| DATA-06 | One event per version with all tickers plus status; removal appears in next snapshot; unchanged version sends nothing | unit + real HTTP | `uv run pytest tests/market/test_stream.py -q` | rewrite |
| DATA-08 | `/api/health` returns `status`, `source`, `note` and matches the SSE status | API | `uv run pytest tests/test_app.py -q` | rewrite |
| DB-01 | Fresh DB gets 6 tables incl. `trades.realized_pnl` and seed (profile $10,000, 10 tickers) | unit (tmp_path) | `uv run pytest tests/db -q` | Wave 0 |
| DB-02 | Second init does not reseed; removed ticker stays removed; foreign-schema DB raises | unit | `uv run pytest tests/db -q` | Wave 0 |
| DB-05 | `db/finally.db` ignored, `.env.example` present with no values | shell | `git check-ignore -q db/finally.db && test -f .env.example` | Wave 0 |
| WATCH-01 | History buffer: windowed, capped, deduped by timestamp, dropped when ticker leaves | Vitest | `npx vitest run src/shared/history.test.ts` | Wave 0 |
| WATCH-02 | `direction` to flash decision (up, down, none for flat) | Vitest + human visual | `npx vitest run`; end-of-phase visual | Wave 0 |
| WATCH-03 | Bad format 400 with message; duplicate 409; LIVE no-data rejection (MockTransport); simulated accepts any well-formed symbol and prices it | API | `uv run pytest tests/test_watchlist_api.py -q` | Wave 0 |
| WATCH-04 | Delete removes and stops tracking; 404 when absent; survives re-lifespan | API | `uv run pytest tests/test_watchlist_api.py -q` | Wave 0 |
| UI-01 | Theme tokens present with the three UI-01 hex values | shell | `grep -c "ecad0a\|209dd7\|753991" frontend/src/app/globals.css` | Wave 0 |
| UI-03 | Connection state transitions (pure function) incl. red after timer and CLOSED handling | Vitest | `npx vitest run src/hooks` | Wave 0 |
| OPS-01 | Image builds; `/`, `/_next/*`, `/api/health`, SSE answer; restart keeps data | container smoke | script in Code Examples | manual script |

### Sampling Rate
- **Per task commit:** `cd backend && uv run pytest -q` (and `npx vitest run` once the frontend exists)
- **Per wave merge:** backend suite + `npm run build` + `npx tsc --noEmit`
- **Phase gate:** full suite green, container smoke script green, then the end-of-phase human visual check (`human_verify_mode: end-of-phase`) of success criteria 1-5 including killing and restarting the container to watch the dot go yellow, red, green

### Wave 0 Gaps
- [ ] `backend/tests/conftest.py` - `DB_PATH` to `tmp_path`, delete `MASSIVE_API_KEY`
- [ ] `backend/tests/db/test_connection.py` - schema, seed once, no reseed, guard
- [ ] `backend/tests/market/test_probe.py`, `test_status.py`; rewrite `test_stream.py`; update `test_app.py`
- [ ] `backend/tests/test_watchlist_api.py` - routes through `httpx.ASGITransport` with the lifespan
- [ ] Frontend: `npm install` per Installation, `vitest.config.mts`, tests for `history`, connection-state and flash-decision helpers
- [ ] `uv add pydantic`

## Security Domain

`security_enforcement` is enabled (absent means enabled; `config.json` sets `true`, ASVS level 1).

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Single-user local app by design; `user_id` default kept |
| V3 Session Management | no | No sessions |
| V4 Access Control | limited | No auth; publish the container on `127.0.0.1` only (`-p 127.0.0.1:8000:8000`) so the open API is not LAN-reachable |
| V5 Input Validation | yes | One `normalize_ticker()` (uppercase, `^[A-Z]{1,5}(\.[A-Z])?$`) before any DB or source; Pydantic body model; parameterised SQL only (`?` placeholders) |
| V6 Cryptography | no | None used; never log or return the Massive key |
| V7 Error handling / logging | yes | Fixed reason strings; no `str(exc)` to clients; keep key in the Bearer header (never in a URL); never log headers |
| V12 Files | yes | `StaticFiles` serves only the export directory (A7 test) |
| V14 Configuration | yes | `.env` gitignored and in `.dockerignore`; `.env.example` has empty values; unquoted values for `--env-file` |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| SQL injection via ticker | Tampering | Regex gate plus `?` placeholders |
| Query-parameter injection into the Massive request | Tampering | Regex gate before `check_ticker`/`add_ticker`; httpx encodes `params` |
| Secret disclosure through probe reason, health, SSE note, or logs | Information disclosure | Reasons are constants; test asserts the key string never appears in `/api/health`, SSE, or captured logs |
| Path traversal through the static mount | Tampering | Starlette `StaticFiles`; one test for `..` requests |
| Unauthenticated API reachable on the LAN | Elevation / Info disclosure | Bind `127.0.0.1` in run commands; document in README |
| Committing DB or `.env` | Information disclosure | `.gitignore` rules plus `.dockerignore`; verified with `git check-ignore` |
| Unbounded SSE clients per tab | Denial of service | Per-client work is a string build at 2 Hz; acceptable at single-user scale |

## Sources

### Primary (HIGH confidence)
- Executed this session: spike Next 16.4.2 + Tailwind 4.3.3 + TS 6.0.3 static export (also in a path with spaces), Vitest 5.0.5 run, FastAPI `StaticFiles` serving through `httpx.ASGITransport`, SQLite init/seed/transaction on Python 3.12.15, multi-stage Docker build and container run, `cd backend && uv run pytest -q` (54 passed), `git check-ignore` runs, read-only inspection of the `finally-data` volume schema.
- Live HTTP: `curl` to `https://api.massive.com/v2/snapshot/locale/us/markets/stocks/tickers?tickers=AAPL` with a bogus Bearer key, no auth, and a bogus `apiKey` query: all `401` with JSON bodies quoted in Pattern 3 (bogus keys only; the real key was never used).
- Installed source read in full: `backend/.venv/Lib/site-packages/fastapi/sse.py`, `fastapi/routing.py:536-670`.
- Repo source read in full: `backend/app/main.py`, `app/market/{stream,cache,models,factory,massive,simulator,interface,seed_data,__init__}.py`, `backend/tests/market/{test_stream,test_app,test_factory}.py`, `test_massive.py` (head), `backend/scripts/watch_prices.py`, `backend/pyproject.toml`, `planning/PLAN.md` §7, `.planning/{REQUIREMENTS,STATE,config.json}`, `.planning/research/{SUMMARY,STACK,PITFALLS,ARCHITECTURE}.md`, `.planning/codebase/CONCERNS.md`.
- npm registry and PyPI via `npm view` and `gsd-tools query package-legitimacy check` on 2026-10-19.
- https://html.spec.whatwg.org/multipage/server-sent-events.html - EventSource failure and reconnection rules (WebFetch).
- https://tailwindcss.com/docs/detecting-classes-in-source-files - gitignored files are not scanned (WebFetch).
- https://massive.com/docs/rest/stocks/snapshots/full-market-snapshot - plan availability, response fields, 3:30 AM EST reset; docs state no HTTP status codes (WebFetch).

### Secondary (MEDIUM confidence)
- STACK.md / PITFALLS.md claims about Massive plans and free-plan end-of-day data (verified there against massive.com pricing and docs on 2026-10-19; not re-fetched here).

### Tertiary (LOW confidence)
- Massive 403/429 bodies and the unknown-ticker response shape (A2, A3): no key available, not captured.
- Context7 MCP requires authentication and was not used; official sites and installed sources were read directly instead.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - versions read from the registry today and exercised in a working build.
- Architecture: HIGH - every integration point was either read in source or executed in a spike.
- Pitfalls: HIGH for the newly found ones (gitignore `lib/`, stale volume schema, tests that break); MEDIUM for Massive 403/429 behaviour.

**Research date:** 2026-10-19
**Valid until:** 2026-11-02 for npm versions (fast-moving: Next, React and postcss all published within the last week); 30 days for the architecture findings.
