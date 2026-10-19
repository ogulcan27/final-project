# Team Contracts

Shared interfaces for the agent team. `PLAN.md` is the spec; this file pins the seams between team-members so they can work in parallel. If you must change a contract, update this file and message the affected owners.

## Ownership

| Member | Owns |
|---|---|
| `database` | `backend/app/db/` (schema.sql, connection, init/seed, repository functions) + `backend/tests/db/` |
| `backend` | `backend/app/main.py`, `backend/app/api/` (routers), `backend/app/services/` (portfolio, watchlist, snapshots) + `backend/tests/api/`, `backend/tests/services/` |
| `llm` | `backend/app/llm/` (prompt, structured output, mock, chat router) + `backend/tests/llm/` |
| `frontend` | `frontend/` |
| `devops` | `Dockerfile`, `.dockerignore`, `docker-compose.yml`, `scripts/`, `.env.example`, root `README.md` |
| `integration` | `test/` (Playwright E2E, `docker-compose.test.yml`) |

`backend/app/market/` is complete; do not change it unless a bug is proven. Only `backend` edits `pyproject.toml` dependencies for the API; `llm` may `uv add litellm` (run from `backend/`). Nobody commits to git; the team lead does.

## Paths and environment

- DB file: env `FINALLY_DB_PATH`; default `<project root>/db/finally.db` (i.e. `backend/../db/finally.db`). Docker sets `FINALLY_DB_PATH=/app/db/finally.db`.
- Static frontend: env `STATIC_DIR`; default `backend/static`. Frontend build output is `frontend/out` (Next.js `output: 'export'`); Docker copies it to the static dir.
- `.env` is read from the project root (`python-dotenv` or docker `--env-file`).
- The DB package lives at `backend/app/db/` (not `backend/db/`) so it cannot collide with the `/app/db` volume mount in the container.

## Database API (`app.db`) - synchronous `sqlite3`

All functions take an optional `user_id: str = "default"`. Timestamps are ISO-8601 UTC strings. Tickers are stored upper-case.

```python
init_db() -> None                      # create tables + seed if missing; idempotent
get_cash(user_id="default") -> float
set_cash(cash: float, user_id="default") -> None
get_watchlist(user_id="default") -> list[str]          # ordered by added_at
add_watchlist(ticker: str, user_id="default") -> bool  # False if already present
remove_watchlist(ticker: str, user_id="default") -> bool  # False if absent
get_positions(user_id="default") -> list[dict]   # {ticker, quantity, avg_cost, updated_at}
get_position(ticker: str, user_id="default") -> dict | None
save_position(ticker: str, quantity: float, avg_cost: float, user_id="default") -> None  # upsert; deletes row if quantity == 0
insert_trade(ticker: str, side: str, quantity: float, price: float, user_id="default") -> dict
insert_snapshot(total_value: float, user_id="default") -> None
get_snapshots(user_id="default") -> list[dict]   # {total_value, recorded_at}, oldest first
insert_chat_message(role: str, content: str, actions: dict | None = None, user_id="default") -> None
get_chat_messages(limit: int = 20, user_id="default") -> list[dict]  # {role, content, actions, created_at}, oldest first
```

## Services (`app.services`) - owned by `backend`, reused by `llm`

```python
class TradeError(Exception): ...       # message is user-facing
execute_trade(cache: PriceCache, ticker: str, side: str, quantity: float) -> dict
    # validates (price known, quantity > 0, enough cash / shares), updates cash, position,
    # trades log, records a snapshot; returns {ticker, side, quantity, price, executed_at}
get_portfolio(cache: PriceCache) -> dict   # shape of GET /api/portfolio
async add_ticker(source: MarketDataSource, ticker: str) -> None     # DB + market source; raises WatchlistError if already present
async remove_ticker(source: MarketDataSource, ticker: str) -> None  # DB + market source (keep tracking if a position is open); raises WatchlistError if absent
class WatchlistError(Exception): ...   # message is user-facing
```

`execute_trade` and `get_portfolio` are sync; `add_ticker` / `remove_ticker` are `async` because the market source methods are.

`app.state.price_cache` and `app.state.market_source` are set in the lifespan. On startup the source tracks watchlist UNION open positions.

## HTTP API (all JSON)

- `GET /api/health` -> `{"status": "ok"}`
- `GET /api/portfolio` -> `{cash_balance, total_value, unrealized_pnl, positions: [{ticker, quantity, avg_cost, current_price, market_value, unrealized_pnl, pnl_pct}]}`
- `POST /api/portfolio/trade` body `{ticker, quantity, side: "buy"|"sell"}` -> `{trade: {...}, portfolio: {...}}`; trade errors (cash, shares, unknown price) -> 400 `{detail: "..."}`; malformed body (e.g. bad `side`) -> 422
- `GET /api/portfolio/history` -> `[{total_value, recorded_at}]`
- `GET /api/watchlist` -> `[{ticker, price, previous_price, change_pct, direction}]` (price fields `null` until the first tick)
- `POST /api/watchlist` body `{ticker}` -> 201 with the item; duplicate -> 409
- `DELETE /api/watchlist/{ticker}` -> 204; absent -> 404
- `POST /api/chat` body `{message}` -> `{message, trades: [{ticker, side, quantity, price, status: "executed"|"failed", error}], watchlist_changes: [{ticker, action: "add"|"remove", status: "executed"|"failed", error}]}`
- `GET /api/chat/history` -> `[{role, content, actions, created_at}]`
- `GET /api/stream/prices` -> SSE, see `MARKET_DATA_SUMMARY.md`

The chat router is `app.llm.router:router`; `backend` includes it in `main.py`.

## LLM mock (`LLM_MOCK=true`)

Deterministic, keyword-based, so E2E tests can rely on it:
- message contains `buy` -> buys 1 share of AAPL
- message contains `sell` -> sells 1 share of AAPL
- message contains `watch` -> adds PYPL to the watchlist
- otherwise -> `{"message": "Mock response: ...", "trades": [], "watchlist_changes": []}`

## Frontend test hooks (for Playwright)

Stable `data-testid`s: `watchlist-row-{TICKER}`, `price-{TICKER}`, `cash-balance`, `total-value`, `connection-status`, `trade-ticker`, `trade-quantity`, `trade-buy`, `trade-sell`, `positions-table`, `position-row-{TICKER}`, `watchlist-add-input`, `watchlist-add-button`, `watchlist-remove-{TICKER}`, `chat-input`, `chat-send`, `chat-message`, `chat-loading`, `heatmap`, `pnl-chart`, `main-chart`.

`connection-status` also carries `data-status="connected|reconnecting|disconnected"`.
