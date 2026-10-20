# FinAlly — AI Trading Workstation

## What This Is

FinAlly (Finance Ally) is a trading-practice workstation for complete beginners who want to learn how trading works. It streams live (real or simulated) market prices, lets the user trade a $10,000 simulated portfolio, and pairs every action with its outcome so the learner sees immediately what a trade did to their profit. It looks like a Bloomberg terminal, but speaks plain language, and an AI coach explains concepts, executes trades on request, and reviews past decisions.

The full product specification lives in `planning/PLAN.md`; this document captures scope, decisions, and additions made on top of it.

## Core Value

A beginner can place a trade and instantly see — on the charts, in the numbers, and in the trade history — how that action affects their profit, with an AI coach ready to explain what happened.

## Requirements

### Validated

<!-- Inferred from existing code (market data layer, 54 passing tests). -->

- ✓ GBM market simulator with correlated moves and random events, ~500ms ticks — existing (`backend/app/market/simulator.py`)
- ✓ Massive (Polygon.io) REST poller implementing the same `MarketDataSource` interface — existing (`backend/app/market/massive.py`)
- ✓ Env-driven source selection (`MASSIVE_API_KEY` set → Massive, else simulator) — existing (`backend/app/market/factory.py`)
- ✓ In-memory shared `PriceCache` with latest/previous price and timestamp — existing (`backend/app/market/cache.py`)
- ✓ SSE price stream at `GET /api/stream/prices` — existing (`backend/app/market/stream.py`)
- ✓ Health check at `GET /api/health` — existing (`backend/app/main.py`)

### Active

**Platform (per `planning/PLAN.md`):**
- [ ] SQLite persistence with lazy init + seed (default user, $10k cash, 10 default tickers), schema per PLAN.md §7
- [ ] Portfolio API: positions, cash, total value, market-order trades with validation, portfolio history snapshots (every 30s + after each trade)
- [ ] Watchlist API: list with prices, add, remove — tracked tickers = watchlist ∪ open positions
- [ ] AI chat via LiteLLM → OpenRouter (Nemotron 3 Super, structured outputs), auto-executing trades and watchlist changes; `LLM_MOCK=true` deterministic mode
- [ ] Next.js static-export frontend served by FastAPI: watchlist with flashing prices + sparklines, main chart, portfolio heatmap, P&L chart, positions table, trade bar, chat panel, header with live total/cash/connection dot
- [ ] Multi-stage Dockerfile, single container on port 8000, volume-mounted `db/`; start/stop scripts for mac/Linux and Windows
- [ ] Unit tests (backend pytest, frontend component tests) and Playwright E2E tests with `docker-compose.test.yml`

**Real market data:**
- [ ] At startup, validate the Massive key with a real snapshot request; if it works use real prices (poll interval per plan), otherwise (free plan / bad key / unreachable) fall back to the simulator and show why
- [ ] Header badge shows the active data source (LIVE vs SIMULATED) and stale-data state

**Backend improvements (from `.planning/codebase/CONCERNS.md`):**
- [ ] True daily change % (simulator keeps a session reference instead of change-since-startup)
- [ ] Batched SSE events (one payload per tick, built once per tick)
- [ ] Stale-data / source status exposed to clients (silent Massive failures become visible)
- [ ] Ticker input validation before reaching any source
- [ ] Watchlist and position changes wired into market tracking (`add_ticker` / `remove_ticker`)
- [ ] `db/*.db` gitignored, committed `.env.example`

**Learning: action ↔ profit visibility:**
- [ ] Buy/sell markers on the main price chart and the portfolio P&L chart
- [ ] Realized P&L (from sells) and unrealized P&L (open positions) shown separately and live
- [ ] Trade blotter: every trade with price and its outcome so far (e.g. "bought 10 AAPL @190 → now +$42 / +2.2%")
- [ ] Instant trade feedback after each trade: cash change, new avg cost, position weight

**Learning: coaching:**
- [ ] Plain-language tooltips on jargon (Unrealized P&L, Realized P&L, Avg Cost, Day %, Weight, etc.)
- [ ] AI coach persona: explains reasoning and concepts in beginner-friendly words, not just executes
- [ ] AI trade review: "review my trades" critiques past decisions using actual trade history and outcomes

**Look & feel:**
- [ ] Bloomberg-terminal aesthetic: dark, dense, monospace numerics, amber accent (`#ecad0a`), blue `#209dd7`, purple `#753991` submit buttons — with plain-language labels so beginners can read it

### Out of Scope

- Candlestick / OHLC charts and technical indicators — user chose line/area price chart; simpler
- Proactive AI comments after trades — AI speaks only when asked (no surprise LLM calls/cost)
- Rule-based automatic hints after trades — not requested
- Simulated micro-ticks between real Massive polls — real mode shows real data only, frozen when market closed
- Limit orders, order book, partial fills, fees — market orders only per PLAN.md
- Authentication / multi-user — single-user local app; `user_id` column kept for future
- Token-by-token chat streaming — complete JSON response + loading indicator per PLAN.md
- Cloud deployment (Terraform/App Runner) — stretch goal, not core build
- Large refactor of the market data layer — fix known concerns, keep existing design

## Context

- **Brownfield.** The market data layer is complete and tested (`backend/app/market/*`, 54 pytest tests). Everything else in `planning/PLAN.md` is unbuilt. Codebase map in `.planning/codebase/`.
- **Spec source.** `planning/PLAN.md` is the authoritative product spec; `planning/MARKET_DATA_SUMMARY.md` summarizes the finished market component.
- **Known issues** listed in `.planning/codebase/CONCERNS.md` (cumulative "daily" %, silent Massive failures, unbounded SSE state, no ticker validation, hard-coded tracked tickers, db not gitignored).
- **Audience.** Complete beginners learning trading — the UI must look professional but every number must be explainable.
- **Course context.** Capstone for an agentic AI coding course; built by coding agents coordinating through `planning/` and `.planning/`.
- **Massive plans (research 2026-10-19):** the free "Stocks Basic" plan has no snapshot endpoint and only end-of-day data (5 calls/min). Snapshot needs a paid plan (Starter/Developer = 15-min delayed, Advanced+ = real-time). The startup check must classify ok / not entitled / bad key / unreachable; anything but ok → simulator, with the reason shown in the UI.

## Constraints

- **Tech stack**: FastAPI + uv (Python 3.12), Next.js TypeScript static export, Tailwind, SQLite, SSE, LiteLLM → OpenRouter — fixed by PLAN.md
- **Packaging**: Python via `uv` only (`uv run`, `uv add`), never pip/python3 directly — user rule
- **Deployment**: single Docker container, single port 8000 — PLAN.md
- **LLM**: `openrouter/nvidia/nemotron-3-super-120b-a12b:free` with `provider.require_parameters: true` and structured outputs, via the openrouter-inference skill — PLAN.md
- **Ports**: app runs in Docker on 8000; local test servers use 8020 — user preference
- **Secrets**: `.env` is never read into agent context; keys only via environment
- **Code style**: simple, incremental, short modules, latest library APIs, no emojis, no defensive over-engineering — user rule
- **Git**: user commits code; `.planning/` docs not committed (`commit_docs: false`)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Build full PLAN.md on top of existing market layer | Market layer is complete and tested | — Pending |
| Bloomberg look, beginner-friendly content ("pro look, friendly guts") | User wants a real trading-app feel for complete beginners | — Pending |
| Line/area main chart, no candles | Simpler; matches PLAN.md minimum | — Pending |
| Massive: validate key at startup, real if valid else simulator, LIVE/SIMULATED badge | User wants real prices when the key works | — Pending |
| Fix CONCERNS.md items, no market-layer refactor | Keep proven design, remove known weaknesses | — Pending |
| Trade markers, realized/unrealized P&L, outcome blotter, instant feedback | Core learning value: see actions and profit together | — Pending |
| AI coach speaks only when asked; can review trade history | Avoid surprise LLM calls; still teaches | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-10-19 after initialization*
