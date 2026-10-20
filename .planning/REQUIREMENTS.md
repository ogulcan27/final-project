# Requirements: FinAlly — AI Trading Workstation

**Defined:** 2026-10-19
**Core Value:** A beginner can place a trade and instantly see — on the charts, in the numbers, and in the trade history — how that action affects their profit, with an AI coach ready to explain what happened.

Product spec: `planning/PLAN.md`. Research: `.planning/research/SUMMARY.md`.

## v1 Requirements

### Market Data (DATA)

- [ ] **DATA-01**: At startup the backend probes the Massive key with one real snapshot request; only an OK response with prices enables real data
- [ ] **DATA-02**: Any non-OK probe (no key, free plan not entitled, bad key, throttled, unreachable, empty) falls back to the simulator with a plain-language reason (never the key)
- [ ] **DATA-03**: User sees a header badge showing LIVE or SIMULATED, with the fallback reason on hover
- [ ] **DATA-04**: User sees a STALE indicator when the active source has not delivered fresh prices within its expected interval
- [ ] **DATA-05**: Day % reflects a true daily reference (previous close in LIVE mode; session reference labelled as such in SIMULATED mode)
- [ ] **DATA-06**: Price stream sends one batched event per update containing all tracked prices plus source/stale status
- [ ] **DATA-07**: Tracked tickers always equal watchlist ∪ open positions, so held tickers keep pricing even after removal from the watchlist
- [ ] **DATA-08**: `GET /api/health` reports status, active source, and fallback reason

### Persistence (DB)

- [ ] **DB-01**: SQLite database is created and seeded automatically on first start (default user, $10,000 cash, 10 default tickers) with no manual setup
- [ ] **DB-02**: Default watchlist is seeded only on a brand-new profile, so removed tickers do not reappear after restart
- [ ] **DB-03**: User's cash, positions, trades, watchlist, snapshots, and chat history persist across container restarts (named Docker volume)
- [ ] **DB-04**: Each sell trade stores its realized P&L at execution time
- [ ] **DB-05**: Database files are gitignored and a committed `.env.example` documents all variables

### Watchlist (WATCH)

- [ ] **WATCH-01**: User sees the watchlist with ticker, live price, Day %, and a sparkline accumulated since page load
- [ ] **WATCH-02**: Prices flash green on uptick and red on downtick, fading within ~500ms
- [ ] **WATCH-03**: User can add a ticker; invalid symbols are rejected with a clear message
- [ ] **WATCH-04**: User can remove a ticker from the watchlist
- [ ] **WATCH-05**: Clicking a watchlist ticker selects it in the main chart and pre-fills the trade bar

### Trading (TRADE)

- [ ] **TRADE-01**: User can buy shares (fractional allowed) at the current price with instant fill and no confirmation dialog
- [ ] **TRADE-02**: User can sell shares they own; selling more than held is rejected
- [ ] **TRADE-03**: Buys exceeding available cash are rejected with a plain-language reason
- [ ] **TRADE-04**: Trades are rejected when the ticker has no price or prices are stale
- [ ] **TRADE-05**: Trade execution is atomic and uses exact money math (weighted-average cost, cent-rounded cash, dust positions removed)
- [ ] **TRADE-06**: Manual trades and AI trades go through the same execution and validation path

### Portfolio (PORT)

- [ ] **PORT-01**: Header shows live total portfolio value, cash, unrealized P&L, realized P&L, and total P&L
- [ ] **PORT-02**: Positions table shows ticker, quantity, avg cost, current price, market value, unrealized P&L ($ and %), and weight
- [ ] **PORT-03**: Portfolio heatmap (treemap) sizes positions by weight and colors them by unrealized P&L
- [ ] **PORT-04**: Portfolio value snapshots are recorded every 30s and immediately after each trade
- [ ] **PORT-05**: Realized + unrealized P&L always equals total value minus $10,000

### Learning: Action ↔ Profit (LEARN)

- [ ] **LEARN-01**: After every trade (manual or AI), user sees an instant feedback card: cash before/after, avg cost before/after, position weight, and realized P&L on sells
- [ ] **LEARN-02**: User sees a trade blotter listing every trade with time, side, quantity, price, and its outcome so far (buys: move since fill; sells: locked-in realized P&L)
- [ ] **LEARN-03**: Main price chart shows buy/sell markers for trades within its visible history
- [ ] **LEARN-04**: P&L chart shows buy/sell markers for all trades
- [ ] **LEARN-05**: Jargon terms (Unrealized P&L, Realized P&L, Avg Cost, Day %, Weight, Market Order, LIVE/SIMULATED, etc.) show plain-language tooltips from one shared glossary

### Charts (CHART)

- [ ] **CHART-01**: User sees a line/area chart of the selected ticker's price over time
- [ ] **CHART-02**: User sees a P&L chart of total portfolio value over time from stored snapshots

### AI Coach (AI)

- [ ] **AI-01**: User can chat with the AI assistant in a docked panel with scrolling history and a loading indicator
- [ ] **AI-02**: AI receives current portfolio context (cash, positions, P&L, watchlist with live prices, recent trades) and recent conversation history
- [ ] **AI-03**: AI can execute trades and watchlist changes from structured output; results (successes and failures) appear inline as action cards
- [ ] **AI-04**: AI explains reasoning and concepts in beginner-friendly language, using the user's real numbers
- [ ] **AI-05**: User can ask the AI to review past trades; it critiques decisions using backend-computed outcomes (the AI never calculates P&L itself)
- [ ] **AI-06**: AI-executed trades are capped at 5 per reply with no duplicate ticker+side
- [ ] **AI-07**: Malformed or failed LLM responses degrade to a plain-text reply with no actions executed
- [ ] **AI-08**: `LLM_MOCK=true` returns deterministic responses covering reply, buy, sell, watchlist change, and failing trade
- [ ] **AI-09**: AI speaks only when the user sends a message (no proactive comments)

### Look & Shell (UI)

- [ ] **UI-01**: Bloomberg-terminal aesthetic: dark background, dense layout, monospace numerics, amber `#ecad0a` accent, blue `#209dd7`, purple `#753991` submit buttons
- [ ] **UI-02**: Labels use plain language readable by a complete beginner
- [ ] **UI-03**: Header shows a connection dot (green connected, yellow reconnecting, red disconnected) that recovers automatically after server restarts
- [ ] **UI-04**: Layout is desktop-first and remains functional on tablet widths
- [ ] **UI-05**: Trade bar has ticker and quantity inputs with Buy and Sell buttons

### Deployment (OPS)

- [ ] **OPS-01**: Single multi-stage Docker image (Node build → Python 3.12 slim) serves frontend and API on port 8000
- [ ] **OPS-02**: Start/stop scripts for macOS/Linux and Windows PowerShell are idempotent; stop keeps data
- [ ] **OPS-03**: App reads keys from `.env` via Docker `--env-file`; secrets are never logged

### Testing (TEST)

- [ ] **TEST-01**: Backend pytest covers market data, trade math (including the realized + unrealized invariant), API routes, and LLM parsing
- [ ] **TEST-02**: Frontend component tests cover rendering, price flash, P&L derivation, and chat states
- [ ] **TEST-03**: Playwright E2E via `test/docker-compose.test.yml` with `LLM_MOCK=true` covers fresh start, watchlist add/remove, buy, sell, charts/heatmap, mocked AI chat trade, and SSE reconnection

## v2 Requirements

Deferred to a future release. Tracked but not in the current roadmap.

### Learning

- **LEARN-V2-01**: Reset portfolio back to $10,000 (with confirm dialog)
- **LEARN-V2-02**: Day P&L per position in positions table
- **LEARN-V2-03**: Sell-row "price since you sold" in blotter
- **LEARN-V2-04**: Persisted price history so chart markers survive reloads

### Extras

- **EXT-V2-01**: Price alerts
- **EXT-V2-02**: CSV export of trades
- **EXT-V2-03**: End-of-day mode using Massive free-plan grouped-daily data

## Out of Scope

| Feature | Reason |
|---------|--------|
| Candlestick/OHLC charts, technical indicators | User chose line/area chart; simpler for beginners |
| Proactive AI comments / rule-based hints after trades | AI speaks only when asked; no surprise LLM calls |
| Simulated micro-ticks between real polls | Real mode shows real data only |
| Limit/stop orders, order book, partial fills, fees, slippage | Market orders only per PLAN.md |
| Shorting, margin, options | Beginner tool; long-only accounting |
| Authentication, multi-user | Single-user local app; `user_id` column kept for future |
| Token-by-token chat streaming | Complete JSON + loading indicator per PLAN.md |
| Trade confirmation dialogs | Deliberate fluid-demo design per PLAN.md |
| Leaderboards, news feeds | Not part of the learning goal |
| Cloud deployment (Terraform) | Stretch goal, not core |
| Market-layer refactor | Fix known concerns only |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| DATA-01 | Phase 1 | Pending |
| DATA-02 | Phase 1 | Pending |
| DATA-03 | Phase 1 | Pending |
| DATA-04 | Phase 1 | Pending |
| DATA-05 | Phase 1 | Pending |
| DATA-06 | Phase 1 | Pending |
| DATA-07 | Phase 2 | Pending |
| DATA-08 | Phase 1 | Pending |
| DB-01 | Phase 1 | Pending |
| DB-02 | Phase 1 | Pending |
| DB-03 | Phase 5 | Pending |
| DB-04 | Phase 2 | Pending |
| DB-05 | Phase 1 | Pending |
| WATCH-01 | Phase 1 | Pending |
| WATCH-02 | Phase 1 | Pending |
| WATCH-03 | Phase 1 | Pending |
| WATCH-04 | Phase 1 | Pending |
| WATCH-05 | Phase 3 | Pending |
| TRADE-01 | Phase 2 | Pending |
| TRADE-02 | Phase 2 | Pending |
| TRADE-03 | Phase 2 | Pending |
| TRADE-04 | Phase 2 | Pending |
| TRADE-05 | Phase 2 | Pending |
| TRADE-06 | Phase 2 | Pending |
| PORT-01 | Phase 2 | Pending |
| PORT-02 | Phase 2 | Pending |
| PORT-03 | Phase 2 | Pending |
| PORT-04 | Phase 3 | Pending |
| PORT-05 | Phase 2 | Pending |
| LEARN-01 | Phase 3 | Pending |
| LEARN-02 | Phase 3 | Pending |
| LEARN-03 | Phase 3 | Pending |
| LEARN-04 | Phase 3 | Pending |
| LEARN-05 | Phase 3 | Pending |
| CHART-01 | Phase 3 | Pending |
| CHART-02 | Phase 3 | Pending |
| AI-01 | Phase 4 | Pending |
| AI-02 | Phase 4 | Pending |
| AI-03 | Phase 4 | Pending |
| AI-04 | Phase 4 | Pending |
| AI-05 | Phase 4 | Pending |
| AI-06 | Phase 4 | Pending |
| AI-07 | Phase 4 | Pending |
| AI-08 | Phase 4 | Pending |
| AI-09 | Phase 4 | Pending |
| UI-01 | Phase 1 | Pending |
| UI-02 | Phase 3 | Pending |
| UI-03 | Phase 1 | Pending |
| UI-04 | Phase 3 | Pending |
| UI-05 | Phase 2 | Pending |
| OPS-01 | Phase 1 | Pending |
| OPS-02 | Phase 5 | Pending |
| OPS-03 | Phase 5 | Pending |
| TEST-01 | Phase 5 | Pending |
| TEST-02 | Phase 5 | Pending |
| TEST-03 | Phase 5 | Pending |

**Coverage:**
- v1 requirements: 56 total
- Mapped to phases: 56
- Unmapped: 0

---
*Requirements defined: 2026-10-19*
*Last updated: 2026-10-19 after roadmap creation (traceability mapped)*
