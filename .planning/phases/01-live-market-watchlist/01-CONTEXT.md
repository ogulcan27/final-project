# Phase 1: Live Market Watchlist - Context

**Gathered:** 2026-10-19
**Status:** Ready for planning

<domain>
## Phase Boundary

Walking skeleton. One Docker image where FastAPI serves a minimal Next.js static export on port 8000. The page shows a live, streaming watchlist (price, Day %, sparkline, green/red flash) fed by one batched SSE event per tick, a header with a LIVE/SIMULATED badge (reason on hover), a STALE indicator, and a connection dot. The user can add and remove tickers. SQLite is created and seeded automatically. The Massive key is probed once at startup, with fallback to the simulator.

Requirements: DATA-01, DATA-02, DATA-03, DATA-04, DATA-05, DATA-06, DATA-08, DB-01, DB-02, DB-05, WATCH-01, WATCH-02, WATCH-03, WATCH-04, UI-01, UI-03, OPS-01.

Not in this phase: trading, portfolio, charts, chat, tracking of positions (DATA-07 is Phase 2), start/stop scripts (Phase 5).

</domain>

<decisions>
## Implementation Decisions

### Carried forward (roadmap / research, already locked)
- **D-01:** Create the full PLAN.md §7 schema now, plus `trades.realized_pnl` (NULL for buys). Later phases must not need a migration. — **Reversibility:** one-way — changing it later needs a migration of the persisted volume DB.
- **D-02:** Seed the default user ($10,000) and the 10 default tickers only when the profile is brand-new. Removed tickers do not come back on restart.
- **D-03:** SSE envelope is frozen as one event per tick: `{prices: [...full snapshot...], status: {source, stale, note}}`. — **Reversibility:** costly — the frontend stores and E2E tests depend on this shape.
- **D-04:** The Massive key is probed once at startup with one real snapshot request. Only OK with prices means LIVE. Anything else (no key, not entitled, bad key, throttled, unreachable, empty) means SIMULATED with a plain-language reason that never includes the key. The source does not switch mid-session.
- **D-05:** `/api/health` returns status, active source, and fallback reason.
- **D-06:** Day %: previous close in LIVE mode. In SIMULATED mode it uses a session reference, labelled as such.
- **D-07:** DB code lives in `backend/app/db/`, not `backend/db/`, to avoid a collision with the `/app/db` volume. The runtime file is `db/finally.db`. `db/*.db*` is gitignored, and `.env.example` is committed.
- **D-08:** Market layer: harden only for the DATA-* items (cache version, batched stream, status/stale, probe, session day-% reference). No refactor.

### Page shell
- **D-09:** Build the full terminal grid now: header, live watchlist, and empty placeholder panels for main chart, positions/heatmap, trade bar, and chat. Each placeholder carries a short label. Later phases fill the panels instead of reshuffling the layout.

### Adding tickers
- **D-10:** Format check in both modes: uppercase-normalize, then `^[A-Z]{1,5}(\.[A-Z])?$`. Malformed input is rejected with a clear message.
- **D-11:** LIVE mode: also reject a well-formed symbol if Massive returns no price for it ("No market data for XYZ").
- **D-12:** SIMULATED mode: any well-formed symbol is accepted and gets a simulated price (uses the simulator's default params for unknown tickers).
- **D-13:** A newly added ticker starts streaming right away (`add_ticker` on the source). Removing it stops tracking it (positions do not exist yet in Phase 1).

### Status badge and STALE
- **D-14:** The header badge reads LIVE or SIMULATED. The fallback reason or source note shows in a hover tooltip, not as inline text.
- **D-15:** STALE threshold is about 3 missed intervals: about 2s for the simulator, about 45s for Massive (3 x 15s poll). Prices frozen because the market is closed count as LIVE, not stale.
- **D-16:** When STALE: the badge turns amber and shows STALE, and watchlist prices dim. Rows are not hidden.
- **D-17:** Connection dot: green when connected, yellow while reconnecting, red when disconnected. It recovers on its own after a server restart.

### Watchlist rows
- **D-18:** Columns: ticker, price, Day %, sparkline, with a remove "x" that shows on row hover.
- **D-19:** The flash covers the price cell only: green on uptick, red on downtick, fading in about 500ms via a CSS transition.
- **D-20:** Sparkline: inline SVG, a rolling buffer of the last ~2-3 minutes of ticks since page load (capped point count).
- **D-21:** Rows keep the order they were added (seed order, then additions at the end).

### Claude's Discretion
- Exact panel proportions, spacing, and placeholder wording within the Bloomberg-style dark theme (UI-01 colors fixed).
- Exact sparkline point cap and the stale threshold constants (within the ranges above).
- Wording of the plain-language fallback reasons and the error messages.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Product spec and scope
- `planning/PLAN.md` — authoritative spec (§6 market data/SSE, §7 schema, §8 endpoints, §10 frontend, §11 Docker)
- `.planning/PROJECT.md` — scope additions and key decisions
- `.planning/REQUIREMENTS.md` — DATA/DB/WATCH/UI/OPS requirement text
- `.planning/ROADMAP.md` — Phase 1 success criteria and notes

### Research
- `.planning/research/SUMMARY.md` — Phase 1 deliverables, envelope shape, versions, deviations from PLAN.md
- `.planning/research/STACK.md` — pinned versions (Next 16.4, Tailwind 4.3, zustand 5, node:24-slim build stage)
- `.planning/research/ARCHITECTURE.md` — component layout, `tracking.py`, probe design
- `.planning/research/PITFALLS.md` — Massive plan entitlement, SSE/EventSource, Next export config, SQLite on Docker

### Existing market layer
- `planning/MARKET_DATA_SUMMARY.md` — summary of the finished market component
- `.planning/codebase/ARCHITECTURE.md`, `.planning/codebase/CONVENTIONS.md`, `.planning/codebase/CONCERNS.md` — patterns and known issues to fix

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/app/market/cache.py` `PriceCache`: latest price per ticker. Add a version counter for batched SSE.
- `backend/app/market/models.py` `PriceUpdate.to_dict()`: per-ticker payload (price, previous_price, prev_close, change_pct, direction, timestamp). Reuse it inside `prices`.
- `backend/app/market/factory.py` `create_market_source`: the place to add the startup probe and fallback reason.
- `backend/app/market/simulator.py` `add_ticker`/`remove_ticker`: idempotent; unknown tickers use `DEFAULT_PARAMS`.
- `backend/scripts/watch_prices.py`: dev SSE client. Update it for the new envelope.

### Established Patterns
- Background sources started/stopped in FastAPI `lifespan`; state on `app.state`.
- Native `fastapi.sse.EventSourceResponse` / `ServerSentEvent`.
- Short modules, frozen slotted dataclasses, `%s` logging, no defensive try/except inside the app.

### Integration Points
- `backend/app/main.py` `lifespan`: replace `DEFAULT_TICKERS` with the watchlist from SQLite (resolves the TODO), and run DB init and seed here.
- `backend/app/market/stream.py` `price_events`: change from per-ticker events to one batched envelope per tick.
- `backend/tests/market/test_stream.py`: tests to update for the new envelope.
- New: watchlist routes, `/api/health` extension, `StaticFiles(html=True)` mounted last, `Dockerfile`.

</code_context>

<specifics>
## Specific Ideas

- "Pro look, friendly guts": Bloomberg-style density with plain-language labels and tooltips.
- Local test servers use port 8020; Docker app on 8000.

</specifics>

<deferred>
## Deferred Ideas

None. The discussion stayed within the phase scope.

</deferred>

---

*Phase: 01-live-market-watchlist*
*Context gathered: 2026-10-19*
