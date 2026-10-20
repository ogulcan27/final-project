# Roadmap: FinAlly — AI Trading Workstation

## Overview

FinAlly grows in five vertical slices on top of the existing, tested market data layer. Phase 1 is the walking skeleton: one Docker image where FastAPI serves a minimal Next.js page with a live watchlist and an honest LIVE/SIMULATED badge. Phase 2 adds the single trade engine and a live portfolio. Phase 3 shows how every trade affects profit (feedback card, blotter, chart markers, glossary tooltips), which is the core learning value. Phase 4 adds the AI coach, which trades through the same engine. Phase 5 adds start/stop scripts, persistence across restarts, and the full test suites.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Live Market Watchlist** - Walking skeleton: Docker image, seeded DB, live streaming watchlist with LIVE/SIMULATED badge
- [ ] **Phase 2: Trading & Live Portfolio** - Single trade engine, trade bar, live P&L header, positions table, heatmap
- [ ] **Phase 3: See Your Profit** - Feedback card, trade blotter, main and P&L charts with trade markers, glossary tooltips
- [ ] **Phase 4: AI Coach** - Chat panel with an AI coach that explains, trades, manages the watchlist, and reviews trades
- [ ] **Phase 5: Ship It** - Start/stop scripts, persistence across restarts, full unit and E2E test suites

## Phase Details

### Phase 1: Live Market Watchlist
**Goal**: As a beginner, I want to open FinAlly and watch real or simulated prices stream into my watchlist, so that I can see the market moving and know whether the data is real.
**Mode:** mvp
**Depends on**: Nothing (first phase)
**Requirements**: DATA-01, DATA-02, DATA-03, DATA-04, DATA-05, DATA-06, DATA-08, DB-01, DB-02, DB-05, WATCH-01, WATCH-02, WATCH-03, WATCH-04, UI-01, UI-03, OPS-01
**Success Criteria** (what must be TRUE):
  1. From a fresh checkout (committed `.env.example` copied to `.env`), building and running the Docker image and opening http://localhost:8000 shows the 10 default tickers with live prices, Day %, and sparklines that fill in since page load, in a dark terminal-style layout. The SQLite file is created automatically and git ignores it.
  2. Prices flash green on an uptick and red on a downtick, and the flash fades within about 500ms. The whole watchlist updates from one batched stream event per tick.
  3. The header badge reads LIVE or SIMULATED. With no key, a free-plan key, a bad key, or no network, the app runs on the simulator and hovering the badge shows a plain-language reason (never the key). `/api/health` reports the same source and reason.
  4. A STALE indicator appears when prices stop arriving within the expected interval. The connection dot is green when connected, yellow while reconnecting, red when disconnected, and turns green again on its own after a server restart. Day % uses previous close in LIVE mode and is labelled as a session reference in SIMULATED mode.
  5. User can add a valid ticker (it starts streaming), sees invalid symbols rejected with a clear message, and can remove a ticker. A removed default ticker does not come back after a restart.
**Plans**: TBD
**UI hint**: yes
**Notes**: Create the full schema here, including `trades.realized_pnl`, so later phases never need a migration. Freeze the batched SSE envelope `{prices, status}` because the frontend depends on it. Research flag: capture live Massive responses (ok / not entitled / bad key / throttled / timeout) and confirm how `fastapi.sse` sends pre-serialized payloads. Change the existing market layer only for the DATA-* hardening items; do not refactor it.

### Phase 2: Trading & Live Portfolio
**Goal**: As a beginner, I want to buy and sell shares from a trade bar and watch my cash, positions, and profit update live, so that I can practice trading with my $10,000.
**Mode:** mvp
**Depends on**: Phase 1
**Requirements**: TRADE-01, TRADE-02, TRADE-03, TRADE-04, TRADE-05, TRADE-06, PORT-01, PORT-02, PORT-03, PORT-05, DB-04, DATA-07, UI-05
**Success Criteria** (what must be TRUE):
  1. User types a ticker and quantity (fractional allowed) into the trade bar and clicks Buy or Sell. The trade fills instantly at the current price with no confirmation dialog, and cash and the positions table update right away.
  2. These trades are rejected with a plain-language reason: buying more than cash allows, selling more shares than held, and trading a ticker that has no price or stale prices.
  3. The header shows live total value, cash, unrealized P&L, realized P&L, and total P&L. The positions table shows ticker, quantity, avg cost, current price, market value, unrealized P&L ($ and %), and weight. The heatmap sizes each position by weight and colors it by unrealized P&L. All of these move with the price stream.
  4. After any sequence of buys and sells, realized plus unrealized P&L equals total value minus $10,000 to the cent. Avg cost follows weighted-average rules, a fully sold position disappears (no dust), and each sell stores its realized P&L. Rapid repeated clicks never overdraw cash.
  5. A ticker the user holds keeps streaming prices after it is removed from the watchlist.
**Plans**: TBD
**UI hint**: yes
**Notes**: `execute_trade` is the only code path that changes cash or positions. It uses one `BEGIN IMMEDIATE` transaction and Decimal money math, and it must be callable without HTTP because Phase 4 AI trades reuse it. Write the accounting tests first, starting with the worked example in research/SUMMARY.md. Decision: reject trades while prices are stale.

### Phase 3: See Your Profit
**Goal**: As a beginner, I want to see right away, on the charts, in the numbers, and in my trade history, what each trade did to my profit, so that I learn how trading decisions turn into gains and losses.
**Mode:** mvp
**Depends on**: Phase 2
**Requirements**: LEARN-01, LEARN-02, LEARN-03, LEARN-04, LEARN-05, CHART-01, CHART-02, PORT-04, WATCH-05, UI-02, UI-04
**Success Criteria** (what must be TRUE):
  1. After every trade, a feedback card shows cash before and after, avg cost before and after, the new position weight, and realized P&L on sells.
  2. A trade blotter lists every trade with time, side, quantity, price, and its outcome so far. Buys show the move since the fill; sells show locked-in realized P&L.
  3. Clicking a watchlist ticker shows its line/area price chart in the main chart area and pre-fills the trade bar. Buy and sell markers appear on that chart for trades inside its visible history.
  4. The P&L chart plots total portfolio value from snapshots taken every 30 seconds and right after each trade, with buy and sell markers for all trades.
  5. Hovering a jargon term (Unrealized P&L, Realized P&L, Avg Cost, Day %, Weight, Market Order, LIVE/SIMULATED) shows a plain-language tooltip from one shared glossary. Labels are readable by a complete beginner, and the full layout stays usable at tablet width.
**Plans**: TBD
**UI hint**: yes
**Notes**: Decision: main-chart markers cover only trades inside the visible window; persisted price history is v2. Research flag: spike Lightweight Charts 5.2 markers (integer-second times, same-second updates, snapping markers to bars). The feedback card component must also render AI trades in Phase 4.

### Phase 4: AI Coach
**Goal**: As a beginner, I want to chat with an AI coach that explains my portfolio in plain words, trades and manages my watchlist when I ask, and reviews my past trades, so that I learn while I trade.
**Mode:** mvp
**Depends on**: Phase 3
**Requirements**: AI-01, AI-02, AI-03, AI-04, AI-05, AI-06, AI-07, AI-08, AI-09
**Success Criteria** (what must be TRUE):
  1. User types into the docked chat panel, sees a loading indicator while waiting, and gets a reply in a scrolling history. The AI never speaks unless the user sends a message.
  2. Asking the AI to buy, sell, or add/remove a watchlist ticker carries out the action through the same engine as the trade bar. Results, successes and failures alike (for example insufficient cash), appear inline as action cards, and the portfolio and watchlist panels update. The AI executes at most 5 trades per reply and never repeats the same ticker and side.
  3. Questions about the portfolio get beginner-friendly explanations that use the user's real cash, positions, P&L, watchlist prices, and recent trades.
  4. Asking "review my trades" returns a critique built on trade outcomes the backend calculated. The AI never computes P&L itself.
  5. With `LLM_MOCK=true`, chat returns deterministic replies for a plain reply, a buy, a sell, a watchlist change, and a failing trade. A malformed or failed LLM response shows a plain-text reply and executes no actions.
**Plans**: TBD
**UI hint**: yes
**Notes**: Write all LLM-calling code with the openrouter-inference skill: `openrouter/nvidia/nemotron-3-super-120b-a12b:free`, `provider.require_parameters: true`, structured outputs, `await acompletion`. Build the mock first. Research flag: run a live Nemotron smoke test (structured-output routing, `$defs`/`$ref` handling, empty content, latency). Serialize chat turns with a lock.

### Phase 5: Ship It
**Goal**: As a beginner, I want to start and stop FinAlly with one script and keep my data between runs, so that I can come back to my portfolio any time, with automated tests proving everything works.
**Mode:** mvp
**Depends on**: Phase 4
**Requirements**: OPS-02, OPS-03, DB-03, TEST-01, TEST-02, TEST-03
**Success Criteria** (what must be TRUE):
  1. Running the start script on macOS/Linux or Windows PowerShell builds the image if needed, starts the container on port 8000 with `.env` and a named volume, and prints the URL. Running it twice is safe. The stop script removes the container and keeps the data.
  2. After a stop and start, cash, positions, trades, watchlist, P&L history, and chat history are all still there.
  3. API keys reach the app only through Docker `--env-file` and never appear in container logs or API responses.
  4. The backend pytest suite (market data, trade math including the realized-plus-unrealized invariant, API routes, LLM parsing) and the frontend component suite (rendering, price flash, P&L derivation, chat states) both pass.
  5. `test/docker-compose.test.yml` runs Playwright with `LLM_MOCK=true` and passes: fresh start, watchlist add/remove, buy, sell, charts and heatmap, mocked AI chat trade, and SSE reconnection after a restart.
**Plans**: TBD
**Notes**: Phases 1-4 each write their own unit tests as they go. TEST-01 and TEST-02 are signed off here as complete suites. Local test servers use port 8020; the Docker app uses 8000.

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Live Market Watchlist | 0/TBD | Not started | - |
| 2. Trading & Live Portfolio | 0/TBD | Not started | - |
| 3. See Your Profit | 0/TBD | Not started | - |
| 4. AI Coach | 0/TBD | Not started | - |
| 5. Ship It | 0/TBD | Not started | - |
