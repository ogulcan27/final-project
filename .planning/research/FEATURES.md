# Feature Research

**Domain:** Paper-trading / trading-education workstation for complete beginners (FinAlly)
**Researched:** 2026-10-19
**Confidence:** MEDIUM overall. Accounting math (weighted average cost, realized/unrealized, invariants) is HIGH (standard, verified by Moomoo / Vanguard / Portfolio Performance docs). Competitor feature inventory is MEDIUM (TradingView and Schwab thinkorswim confirmed from official pages; Investopedia and Webull specifics are from general knowledge plus thin or third-party search results, so treat those rows as LOW-MEDIUM). Beginner-UX recommendations are opinionated synthesis (MEDIUM).

Scope guard (from PROJECT.md Out of Scope): no candles or indicators, no proactive AI comments, no rule-based auto hints, no limit orders or fees, no auth, no token streaming, no simulated micro-ticks in real mode.

## Feature Landscape

### Table Stakes (Users Expect These)

Missing any of these and the product feels like a toy or is not a trading simulator at all.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Starting virtual cash + visible cash balance | Every simulator (Investopedia, TradingView, paperMoney, Webull) starts with a fixed pot and shows it | LOW | $10k in header. Also show "Buying power" as plain "Cash available" (no margin, so they are equal) |
| Live-updating watchlist (price, day change %, flash) | Core of every terminal UI | LOW | Already specified. Day % must be true daily change vs previous close (CONCERNS.md item), otherwise the number lies |
| Market buy/sell with instant fill | Minimum order type in all simulators | LOW | Server validates: cash >= qty*price for buys, qty <= owned for sells. Reject shorting (see Anti-Features). Fractional quantity allowed per PLAN.md |
| Positions table (ticker, qty, avg cost, price, unrealized P&L $ and %) | Every broker's "Positions" tab (TradingView Positions tab, thinkorswim Position Statement) | LOW | Add "Weight %" and "Market value" columns. Live-update from SSE |
| Total portfolio value + total P&L in header | Investopedia and Webull lead with account value and day/total gain | LOW | Show Total value, Cash, and Total P&L ($ and % vs $10k start) |
| Trade history list | TradingView has History / Account history; Investopedia has Trade History; paperMoney has Monthly Statement | LOW | Here upgraded to the "trade blotter" differentiator below. Plain history is the floor |
| Price chart for selected ticker | Universal | MEDIUM | Line/area only (per PROJECT.md). Backed by accumulated SSE ticks since page load, so trades made before reload fall off the left edge (see PITFALLS) |
| Portfolio value over time chart | Investopedia "performance" graph, Webull account curve | MEDIUM | `portfolio_snapshots` every 30 s plus one right after each trade |
| Add / remove watchlist ticker with validation | Universal | LOW | Reject unknown/invalid symbols with a friendly message; tracked tickers = watchlist union open positions, so removing a held ticker from the watchlist must not stop its price updates |
| Clear error messages on rejected trades | Simulators reject silently or cryptically; beginners need to know why | LOW | "Not enough cash: you need $1,900.00 but have $1,200.00." Same text reused in chat and trade bar |
| Connection / data-source status | Real terminals show feed status | LOW | Dot (green/yellow/red) plus LIVE vs SIMULATED badge plus stale state. Beginners must not mistake simulated prices for real ones |
| Persistence across restarts | Accounts persist in every product | LOW | SQLite volume. Portfolio survives `docker stop` |

### Differentiators (Competitive Advantage)

These align directly with the Core Value in PROJECT.md: "place a trade and instantly see how that action affects profit, with an AI coach ready to explain."

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Buy/sell markers on main price chart | Links the action to the price path ("I bought right before the drop"). Few simulators show your own fills on a line chart; TradingView does on candles | MEDIUM | Lightweight Charts v5 series-markers plugin (`createSeriesMarkers`) with up-arrow green for buy and down-arrow for sell, tooltip "Bought 10 @ $190.00". Marker time must snap to an existing data point. Only trades within the in-memory price window can be drawn |
| Buy/sell markers on P&L (portfolio value) chart | Shows what each trade did to the equity curve | MEDIUM | Natural fit because a snapshot is recorded immediately after each trade, so a marker can sit exactly on a data point |
| Realized vs unrealized P&L displayed side by side, live | Most beginner apps show one blended "gain" number. Separating "locked in" from "on paper" is the single most useful concept to teach | MEDIUM | Header or portfolio card: Realized $, Unrealized $, Total $. Realized stored per trade at sale time (see Calculation Spec) |
| Trade blotter with "outcome so far" per trade | Answers "was that a good trade?" without the learner doing math | MEDIUM | Columns: time, side, ticker, qty, fill price, "Since then" ($ and %), and for sells "Realized". Live-updates from SSE. Wording in Calculation Spec |
| Instant post-trade feedback card | Immediate cause-and-effect: cash change, new avg cost, new position weight | LOW-MEDIUM | Returned in the `/api/portfolio/trade` response (cash before/after, qty before/after, avg cost before/after, weight after, realized P&L if sell). Shown as an inline toast or card, no confirmation dialog beforehand |
| Plain-language jargon tooltips | Bloomberg look with friendly guts. Real terminals assume expertise; beginner apps dumb down the look. Doing both is the niche | LOW | Single `glossary` map in the frontend, one `<Term>` component wrapping column headers and labels. Content list in Jargon section below. Static text, no LLM calls |
| AI coach persona that explains, not just executes | Chat apps in this space either do trades or answer FAQs; coaching with the user's own numbers is differentiating | LOW-MEDIUM | System prompt change plus portfolio context already planned. Keep answers short, define terms on first use, explain the "why" of every suggested trade |
| AI "review my trades" on request | Personalized feedback from real history, like a mentor | MEDIUM | On request only (no proactive calls). Backend computes all numbers (per-trade outcome, realized total, win rate, concentration) and injects them into the prompt; the LLM only narrates. Never let the LLM compute P&L |
| LIVE vs SIMULATED badge with stale warning | Honest data provenance. Competitors hide it | LOW | Needs backend status exposed to clients (already in Active requirements) |
| Chat actions rendered inline as confirmations | Teaches that the AI actually changed the portfolio | LOW | Reuses the same trade-feedback card in the chat bubble. Failed validations shown inline with the reason |
| Portfolio treemap heatmap (size = weight, color = P&L) | Finviz-style at-a-glance concentration view. Webull and Investopedia offer lists, not heatmaps | MEDIUM | Recharts Treemap or custom SVG/canvas. Color scale clamped (e.g. +/-5%) so small moves are visible. Label shows ticker and unrealized % |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Candlesticks and technical indicators (RSI, MACD, SMA) | TradingView and thinkorswim have them; looks "pro" | Out of Scope. Needs OHLC history the simulator does not generate; teaches chart-reading before basic P&L; large UI surface | Line/area chart with trade markers |
| Limit / stop orders, order book, partial fills | Real brokers have them | Out of Scope. Introduces pending-order state, fill engine, cancel flows, and Massive free-tier 15 s data cannot support realistic triggers | Market orders only; note it in a tooltip ("Market order: buy right now at the current price") |
| Short selling, margin, options | thinkorswim and Investopedia support them | Breaks the simple model (negative quantity, borrow, margin calls) and confuses beginners | Reject sell > owned with a clear message |
| Fees, commissions, slippage simulation | Realism | Out of Scope; also makes realized+unrealized = total-10k invariant harder to explain | Mention in a tooltip that real brokers differ |
| Proactive AI comments after each trade | "Coach should react" | Out of Scope. Surprise LLM calls, cost, latency, noisy, free model rate limits | The deterministic post-trade feedback card is the instant reaction; AI only when asked |
| Rule-based automatic hints ("you are 60% in tech") | Cheap teaching | Out of Scope; also drifts toward unsolicited advice | Weight column and treemap make concentration visible; user can ask the coach |
| Trade confirmation dialog | Safety | Contradicts PLAN.md ("no confirmation dialog", instant, fluid demo). Fake money | Instant feedback card with the result |
| Leaderboards, social, achievements, streaks | Gamification in Investopedia contests | Needs multi-user and auth; also encourages reckless risk-taking | None |
| Real news feed, earnings calendar, fundamentals | Terminals have them | Data licensing, scope blow-up, not about the action-to-profit loop | Link out is not needed; skip |
| Price alerts and notifications | Webull and TradingView have them | Needs background evaluation, notification channel, state | Defer; none for v1 |
| Tax lots (FIFO/LIFO/specific lot), wash-sale, tax reports | Real brokers | Huge complexity, irrelevant to a simulator | Single weighted-average cost method only (see Calculation Spec) |
| Per-trade chart replay / backtesting (thinkBack-style) | thinkorswim | Requires historical data store | Out of scope |
| Streaming chat tokens | "Feels modern" | Out of Scope per PLAN.md; complicates structured-output parsing | Loading indicator |
| Multiple paper accounts, CSV export, AI-driven auto-trading without being asked | TradingView offers multiple accounts and CSV export | Needless scope for single-user v1; autonomous trading violates "speaks only when asked" | Defer |

### Possibly worth adding (not in PROJECT.md, decide at requirements time)

| Feature | Value | Complexity | Notes |
|---------|-------|------------|-------|
| "Reset portfolio" button (back to $10k, clear positions/trades/snapshots) | TradingView supports reset; beginners will want a fresh start after a bad run | LOW | One backend endpoint plus a confirm step. This is the only place a confirmation dialog is justified, because it is destructive. Recommended P2 |
| "Since you started" total return label | Simple anchor for total P&L | LOW | `total_value - 10000`; trivial once header exists |

## Feature Dependencies

```
Market data stream (existing)
    └──requires──> Price cache + tracked tickers (watchlist union positions)
                       └──requires──> Ticker validation

SQLite schema (+ trade columns: realized_pnl, avg_cost_after, cash_after)
    └──requires──> Trade execution service (validate, update cash/position, write trade, write snapshot)
                       ├──requires──> Positions table + header totals (cash, value, realized, unrealized)
                       ├──requires──> Instant trade feedback card (same response payload)
                       ├──requires──> Trade blotter (outcome so far)
                       ├──requires──> Portfolio snapshots ──requires──> P&L chart ──enhances──> P&L chart markers
                       └──requires──> Treemap heatmap (positions + weight)

Price chart (SSE accumulation) ──enhances──> Main chart trade markers
Trade markers (both charts) ──requires──> Trade list with timestamps (blotter data)

Jargon tooltips ──enhances──> Positions table, blotter, header, feedback card (build glossary early so every table uses it)

Chat endpoint ──requires──> Trade execution service (same code path as manual trades)
AI coach persona ──requires──> Chat endpoint + portfolio context
AI trade review ──requires──> Trade blotter computation (server-side outcomes) ──requires──> Trade execution service

LIVE/SIMULATED badge ──requires──> Source status exposed to clients ──requires──> Massive key validation at startup
Stale state ──requires──> Source status exposed to clients

Limit orders ──conflicts──> "market only, instant fill, no pending state" model
Proactive AI comments ──conflicts──> "AI speaks only when asked"
```

### Dependency Notes

- **Trade execution service is the keystone.** Manual trade bar, chat auto-execution, feedback card, blotter, snapshots, markers all hang off one function. Build it once, with pure functions for the math, and unit-test it hard.
- **Schema must carry per-trade accounting from day one.** PLAN.md's `trades` table has only ticker/side/quantity/price/executed_at. Adding `realized_pnl` (null for buys) and `avg_cost_after` (and optionally `cash_after`) at write time avoids recomputing history later and lets the AI review read ground truth. This is a schema deviation from PLAN.md section 7 and needs an explicit decision (the lazy-init schema makes it cheap now, expensive later).
- **Tooltips before tables.** The glossary component is trivial but touching every table later is churn; create it before positions/blotter/header.
- **Markers depend on chart time axes.** The main chart's time axis is "since page load"; trade markers older than that cannot be drawn without persisting price history. Decide either (a) accept the limitation and show markers only in-window, or (b) persist a small rolling price history. (a) is the simple recommendation.
- **AI review depends on server-computed outcomes.** Build blotter outcomes in backend code (reused for UI and LLM prompt), do not recompute in the frontend separately, to keep one source of truth.

## MVP Definition

### Launch With (v1)

- [ ] Trade execution service with weighted-average cost, realized P&L stored on sells, rejection rules and clear messages (foundation for everything)
- [ ] Portfolio API returning positions with market value, weight, unrealized P&L; header totals: cash, total value, realized, unrealized, total P&L
- [ ] Watchlist with flash/sparklines, add/remove with validation
- [ ] Main price chart (line/area) plus P&L chart, both with buy/sell markers
- [ ] Positions table with Weight column
- [ ] Trade blotter with "since then" outcome and realized column
- [ ] Instant post-trade feedback card (manual and chat)
- [ ] Jargon tooltips on the term list below
- [ ] Treemap heatmap
- [ ] LIVE/SIMULATED badge, connection dot, stale state
- [ ] AI chat with coach persona, auto-execute, inline confirmations, mock mode
- [ ] AI "review my trades" (same chat endpoint, history plus computed outcomes injected when asked)

### Add After Validation (v1.x)

- [ ] Reset portfolio button: once users blow up an account and want to restart
- [ ] Day P&L per position ($ change today): when beginners ask "how did I do today"
- [ ] Marker hover cards linking to blotter rows: if marker clutter or confusion appears
- [ ] Persisted rolling price history so markers survive page reloads

### Future Consideration (v2+)

- [ ] Price alerts
- [ ] CSV export of trades
- [ ] Multiple accounts / scenarios (e.g. "compare two strategies")
- [ ] Candles and indicators (explicitly Out of Scope now)

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Trade execution + avg cost + realized P&L | HIGH | MEDIUM | P1 |
| Positions table + header totals (cash/value/realized/unrealized) | HIGH | LOW | P1 |
| Instant feedback card | HIGH | LOW | P1 |
| Trade blotter with outcomes | HIGH | MEDIUM | P1 |
| Jargon tooltips | HIGH | LOW | P1 |
| Watchlist, sparklines, flash | HIGH | LOW | P1 |
| Main chart + P&L chart | HIGH | MEDIUM | P1 |
| Trade markers on both charts | HIGH | MEDIUM | P1 |
| LIVE/SIMULATED badge + stale | HIGH | LOW | P1 |
| AI chat with auto-execute | HIGH | MEDIUM | P1 |
| AI coach persona | HIGH | LOW | P1 |
| AI trade review | MEDIUM-HIGH | MEDIUM | P1 (core value, but build after blotter) |
| Treemap heatmap | MEDIUM | MEDIUM | P1 (in PLAN.md) |
| Reset portfolio | MEDIUM | LOW | P2 |
| Day P&L per position | MEDIUM | LOW | P2 |
| Persisted price history for markers | LOW-MEDIUM | MEDIUM | P3 |
| Alerts, CSV, multi-account | LOW | MEDIUM | P3 |

**Priority key:** P1 must have for launch; P2 should have when possible; P3 nice to have.

## Competitor Feature Analysis

| Feature | Investopedia Simulator | TradingView Paper | thinkorswim paperMoney | Webull Paper | Our Approach |
|---------|-----------------------|-------------------|------------------------|--------------|--------------|
| Starting cash | Large default (reported $100k to $1M depending on game) | Default $100k, configurable | $100,000 virtual | Configurable | $10,000; small number makes each trade meaningful |
| Order types | Market, limit, stop, short, options | Market, limit, stop, brackets | Full set (options, futures, forex) | Market, limit, stop | Market only |
| Positions / P&L | Portfolio tab with gain/loss | Positions tab with PnL | Position Statement | Positions with P&L | Positions with realized/unrealized split |
| Trade history | History tab | History, Account history (realized PnL), Trading journal tabs | Monthly Statement / Activity | Order history | Blotter with "outcome so far" |
| Chart markers for own trades | Not a focus | Yes (on candles) | Yes (on candles) | Limited | Yes, on line chart and P&L chart |
| Realized vs unrealized | Shown as gain/loss, not emphasized | Realized PnL in Account history | P&L Open vs P&L Day/YTD | Shown | Always side by side, with explanations |
| Education | Articles and courses elsewhere on site | Minimal | Separate education center | Light | Inline tooltips plus AI coach with the user's own numbers |
| AI assistant | None | None (as of research) | None | None | Chat that explains, executes, reviews |
| Market data realism | Delayed quotes | Real, per feed | Real-time, simulated fill, no after-hours fills | Real | Simulator by default, real if key validates, badge states which |
| Simulation realism caveats | No slippage, instant fills | Same | Theoretical fill price, no slippage, perfect liquidity | Same | State in tooltip: fills at displayed price, no fees |

Takeaway: incumbents are broad (many asset types, order types, indicators) and shallow on teaching. FinAlly wins by being narrow (market orders, equities only) and deep on action-to-outcome explanation.

## Calculation Spec (feeds requirements and tests)

Use one method everywhere: **weighted (moving) average cost, long-only, no fees.** Only buys change average cost; sells never change it. (Confirmed by Moomoo's average-cost example and Portfolio Performance's moving-average method; Vanguard documents that average cost is distinct from lot methods, so do not expose FIFO.)

### Formulas

Definitions: `q` current quantity, `a` average cost per share, `p` current market price, `cash`, `S` starting cash (10,000).

| Quantity | Formula | Notes |
|----------|---------|-------|
| Buy of `n` at price `x` | `a' = (a*q + x*n) / (q + n)`; `q' = q + n`; `cash' = cash - x*n` | If `q == 0`, `a' = x` |
| Sell of `n` at price `x` (`n <= q`) | `realized = (x - a) * n`; `q' = q - n`; `a' = a` (unchanged); `cash' = cash + x*n` | If `q' == 0`: close position (delete row or set qty 0) and discard `a` |
| Market value (position) | `p * q` | |
| Cost basis (position) | `a * q` | |
| Unrealized P&L ($) | `(p - a) * q` | |
| Unrealized P&L (%) | `(p / a - 1)` i.e. `(p - a) / a` | Guard divide by zero |
| Realized P&L (total) | sum of `realized` stored on every sell trade | Persist at sale time. Never recompute from history with a different method |
| Total portfolio value | `cash + sum(p*q)` | |
| Total P&L | `total_value - S` | |
| **Invariant (test this)** | `realized_total + unrealized_total == total_value - S` | Holds exactly because there are no fees. Make it a property-style unit test; any drift means a bug |
| Position weight | `position_market_value / total_portfolio_value` | Denominator includes cash, so weights plus cash % = 100%. Show cash % in the heatmap legend or header |
| Treemap tile area | position market value (relative weights among invested positions) | Tile color = unrealized %, not weight |
| Day change % | `(price - previous_close) / previous_close` | Needs true previous close, per CONCERNS.md |

### Per-trade outcome ("outcome so far")

Because average cost is pooled, buys are not tied to lots. Define outcomes per trade as metrics versus that trade's own fill price, and say so.

- **Buy row:** `since_then = (p_now - fill_price) * qty` and `% = p_now / fill_price - 1`. Label: "Since you bought". This is "what this purchase is worth now vs what you paid", not the position's P&L. If the position has been sold down, the number is still informative about the entry price, but display "(partly sold)" to prevent a mismatch with the realized/unrealized totals.
- **Sell row:** primary = `realized` stored at sale ("Locked in: +$75.00, sold at $210 vs your average cost $195"). Secondary (optional) = move since sale `(p_now - fill_price)` per share and percent: "Price is $5 lower since you sold" (positive framing: selling looked good; negative framing: could have held). This teaches without judging.
- Always show "now" price and time, and update live from SSE. Outcome text for the AI review is produced by the same server function.

Do not label a buy's outcome as realized. Do not sum blotter outcomes and expect them to equal portfolio totals; explain with a tooltip on the column header ("Compares each trade to today's price. Your Positions table shows the combined result.").

### Worked example (use for unit tests and tooltip copy)

| Step | Cash | Qty | Avg cost | Notes |
|------|------|-----|----------|-------|
| Start | 10,000.00 | 0 | n/a | |
| Buy 10 AAPL @190 | 8,100.00 | 10 | 190.00 | weight = 1,900 / 10,000 = 19.0% |
| Buy 10 AAPL @200 | 6,100.00 | 20 | 195.00 | `(190*10 + 200*10)/20` |
| Price moves to 205 | 6,100.00 | 20 | 195.00 | unrealized = `(205-195)*20 = +200` (+5.13%), total value 10,200, weight = 4,100/10,200 = 40.2% |
| Sell 5 @210 | 7,150.00 | 15 | 195.00 (unchanged) | realized = `(210-195)*5 = +75`; unrealized at 205 = `(205-195)*15 = +150`; total value = 7,150 + 3,075 = 10,225; check: 75 + 150 = 225 = 10,225 - 10,000 |
| Blotter at p=205 | | | | Buy#1: +150 (+7.9%); Buy#2: +50 (+2.5%); Sell: locked +75, price -2.4% since sale |

### Display rules

- Color and sign: green with `+`, red with `-`, neutral gray for exactly 0. Monospace, right-aligned numerics, fixed decimals (2 for money, up to 4 for fractional quantity, trimmed).
- Show both $ and % for any P&L.
- Rounding: store full floats, round only at display. Treat `|q| < 1e-9` as closed. Reject trades with quantity <= 0 or non-finite.
- Header order: Total value, Cash, Unrealized, Realized, Total P&L. Each wrapped in a `<Term>` tooltip.
- Instant feedback card contents: "Bought 10 AAPL @ $190.00. Cash $10,000.00 -> $8,100.00. Position 0 -> 10 shares, average cost $190.00. This position is 19.0% of your portfolio." For sells add "Realized +$75.00 (sold at $210.00, your average cost was $195.00)."

## Jargon Needing Tooltips (ranked by beginner confusion)

Tier 1 (must have, appear in default view):

| Term | Plain-language tooltip (draft) |
|------|--------------------------------|
| Unrealized P&L | "Profit or loss on shares you still hold, if you sold at the current price. It can change until you sell." |
| Realized P&L | "Profit or loss you locked in by selling. It does not change after the sale." |
| Avg Cost | "The average price you paid per share, weighted by how many you bought at each price." |
| Day % / Day Change | "How much the price has moved since yesterday's close." (Must be true daily change.) |
| Weight | "How much of your total portfolio value this position makes up." |
| Total P&L | "Your total profit or loss since you started with $10,000: realized plus unrealized." |
| P&L | "Profit and Loss: how much money you have made or lost." |
| Market Order | "Buy or sell right now at the current price." |
| Position | "The shares you currently own of one company." |
| Quantity / Shares | "How many shares. You can own fractions of a share here." |
| Cash / Buying power | "Money available to buy. Selling adds to it, buying subtracts from it." |
| Portfolio value / Total value | "Cash plus the current value of all your shares." |
| Ticker | "The short code for a company, like AAPL for Apple." |
| Watchlist | "Stocks you are tracking. Watching does not cost anything or mean you own them." |
| LIVE vs SIMULATED | "LIVE: real market prices. SIMULATED: made-up prices that move like a real market, for practice." |

Tier 2 (add where the term is visible):

| Term | Plain-language tooltip (draft) |
|------|--------------------------------|
| Market value | "What your shares are worth right now: shares times current price." |
| Cost basis | "Total money you paid for the shares you still hold." |
| Heatmap / Treemap | "Each box is a stock you own. Bigger box = bigger share of your portfolio. Green = profit, red = loss." |
| Sparkline | "A tiny chart of recent price moves." |
| Since then / Since you bought | "Compares today's price with the price you paid on that trade." |
| Buy / Sell markers | "Arrows on the chart where you traded." |
| Fill price | "The price your trade was executed at." |
| Concentration | "Having a large share of your money in one stock. Riskier because one bad day hurts more." |
| Diversification | "Spreading money across several stocks so one bad one hurts less." |
| Stale data | "The prices have not updated recently, so they may be out of date." |
| Uptick / Downtick | "Price just rose or fell." (Only if the term appears in UI copy; prefer plain words.) |

Avoid introducing jargon not on this list (bid/ask, spread, volume, P/E, margin). If a term is not defined, do not show it.

## Sources

- TradingView official help: Paper Trading main functionality and Account manager (tabs: Positions, Orders, History, Account history, Trading journal; account reset deletes orders, history and positions): https://www.tradingview.com/support/solutions/43000516466-paper-trading-main-functionality/ and https://in.tradingview.com/support/solutions/43000786138-what-is-the-account-manager/ (MEDIUM-HIGH)
- Schwab thinkorswim paperMoney page (virtual funds, real-time data, P&L analysis; simulated executions): https://www.schwab.com/trading/thinkorswim/paper-trading (MEDIUM-HIGH; limitation details from secondary commentary, MEDIUM-LOW)
- Moomoo average-cost method example (sell leaves average unchanged, realized P&L booked; buy formula): https://www.moomoo.com/au/support/topic6_37 (MEDIUM-HIGH)
- Vanguard cost basis methods (average cost vs lot methods): https://investor.vanguard.com/taxes/cost-basis/ (HIGH for concept)
- Portfolio Performance cost methodology (moving average vs FIFO): https://help.portfolio-performance.info/en/concepts/cost-methodology/ (MEDIUM)
- Investopedia simulator and Webull paper trading: official feature pages not retrievable via search; rows in the competitor table are from general product knowledge plus third-party discussion (https://discussion.fool.com/t/simulated-investopedia-portfolio/53243), LOW-MEDIUM. Verify before quoting any starting balance or order-type claim.
- Project docs: `.planning/PROJECT.md`, `planning/PLAN.md` (scope and Out of Scope list)
- Accounting identities and worked example derived and hand-checked in this document (HIGH, verify with unit tests).

---
*Feature research for: beginner paper-trading / trading-education workstation*
*Researched: 2026-10-19*
