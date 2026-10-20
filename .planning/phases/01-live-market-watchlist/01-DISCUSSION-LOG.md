# Phase 1: Live Market Watchlist - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-10-19
**Phase:** 01-live-market-watchlist
**Areas discussed:** Page shell scope, Adding tickers, Status badge & STALE, Watchlist row look (accepted as a set of defaults)

---

The user asked whether everything to implement was already decided. Claude explained that the technical decisions were settled by PLAN.md, REQUIREMENTS.md, and research. It then proposed defaults for the four remaining product gray areas.

## Defaults

| Option | Description | Selected |
|--------|-------------|----------|
| Accept all | Lock the 4 proposed defaults and write CONTEXT.md | ✓ |
| Discuss some | Go through one or more areas first | |

**Defaults accepted:**
- Page shell: full terminal grid with placeholder panels
- Adding tickers: format regex in both modes; LIVE also requires a Massive price; SIMULATED accepts any well-formed symbol
- Badge/STALE: reason in hover tooltip; stale after about 3 missed intervals; amber badge plus dimmed prices
- Rows: ticker, price, Day %, sparkline; price-cell flash; 2-3 minute sparkline; insertion order; hover "x" to remove

## Claude's Discretion

Panel proportions, placeholder wording, sparkline cap, stale constants, reason and error wording.

## Deferred Ideas

None.
