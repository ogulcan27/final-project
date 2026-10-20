# API Coverage: Massive (Polygon.io) REST

> Full coverage by default. Opt-outs are explicit, reasoned decisions.
> Phase 1 uses Massive only as an optional live price source behind the `MarketDataSource` interface (PLAN.md section 6). Without a key, the simulator is used.

| capability | decision | reason |
|---|---|---|
| multi-ticker stocks snapshot (/v2/snapshot/locale/us/markets/stocks/tickers) | INTEGRATE | |
| single-ticker snapshot | OPT-OUT | not needed: the multi-ticker snapshot with tickers=X covers the startup probe and the add-ticker check (D-11) |
| top gainers and losers snapshot | OPT-OUT | explicitly out of scope: no market-movers view in the product |
| aggregates and bars (historical OHLC) | OPT-OUT | not needed yet: historical charts are v2 (LEARN-V2-04); Phase 1 charts accumulate from the stream |
| grouped daily bars | OPT-OUT | not needed yet: deferred with EXT-V2-03 |
| daily open and close | OPT-OUT | not needed: the snapshot carries prevDay.c for Day % (D-06) |
| previous close endpoint | OPT-OUT | not needed: prevDay.c in the snapshot already gives the previous close |
| last trade and last quote | OPT-OUT | not needed: the snapshot carries the latest trade price |
| market status and holidays | OPT-OUT | not needed: a closed market still returns HTTP 200 with frozen prices and counts as LIVE, not stale (D-15) |
| reference tickers search | OPT-OUT | not needed: add-ticker validation uses the snapshot (D-11) |
| websocket streaming | OPT-OUT | explicitly out of scope: PLAN.md section 6 mandates REST polling for all tiers |
| technical indicators | OPT-OUT | explicitly out of scope: not part of the beginner trading product |
| news | OPT-OUT | explicitly out of scope: not part of the product specification |
| financials, dividends and splits | OPT-OUT | explicitly out of scope: simulated portfolio uses price only |
| options, forex, crypto and indices | OPT-OUT | explicitly out of scope: US stocks only |
