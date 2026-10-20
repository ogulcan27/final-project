# Phase 1: Live Market Watchlist - Pattern Map

**Mapped:** 2026-10-19
**Files analyzed:** 33 (new/modified)
**Analogs found:** 19 / 33 (all backend; frontend and Docker have no in-repo analog)

All analog paths below were confirmed git-tracked (`git ls-files` in `backend/`). Paths are relative to `backend/` unless noted.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match |
|---|---|---|---|---|
| `app/market/cache.py` (mod: `version`) | store | CRUD | itself (`app/market/cache.py:9-43`) | self |
| `app/market/interface.py` (mod: `kind`, `last_ok`, `stale_after`, `check_ticker`) | interface | request-response | itself (`interface.py:11-30`) | self |
| `app/market/simulator.py` (mod: kind, last_ok in `step`) | service | event-driven | itself (`simulator.py:68-79`) | self |
| `app/market/massive.py` (mod: `probe_massive`, `last_ok`, `check_ticker`) | service | request-response | itself (`massive.py:86-107`) | self |
| `app/market/factory.py` (mod: `start_market_source`) | factory | request-response | itself (`factory.py:9-15`) | self |
| `app/market/status.py` (new: `build_status`) | utility | transform | `app/market/models.py` (small pure value logic) | role-match |
| `app/market/stream.py` (mod: batched envelope) | route/generator | streaming | itself (`stream.py:16-37`) | self |
| `app/main.py` (mod: lifespan, routers, 404, static) | config/entry | request-response | itself (`main.py:10-31`) | self |
| `app/config.py` (new) | config | n/a | env read in `app/market/factory.py:11-13` | partial |
| `app/context.py` (new: frozen Context) | model | n/a | `PriceUpdate` frozen dataclass (`app/market/models.py`) | role-match |
| `app/schemas.py` (new: `normalize_ticker`, `WatchlistAdd`) | utility | transform | none in repo (FastAPI/pydantic default) | no analog |
| `app/db/schema.sql`, `app/db/connection.py`, `app/db/watchlist.py` | model/store | CRUD | none (no sqlite yet); use RESEARCH Pattern 5 | no analog |
| `app/services/tracking.py`, `app/services/watchlist.py` | service | CRUD | `app/market/simulator.py` add/remove idempotence | partial |
| `app/routes/watchlist.py`, `app/routes/system.py` | route | request-response | `app/market/stream.py:33-37` router + `main.py:29-31` health | role-match |
| `tests/db/test_*.py`, `tests/services/*`, `tests/routes/*` (new) | test | request-response | `tests/market/test_app.py`, `test_stream.py` | role-match |
| `tests/market/test_stream.py`, `test_app.py` (rewrite), `test_massive.py` (+probe tests), new `test_status.py`, `conftest.py` | test | streaming | itself | self |
| `scripts/watch_prices.py` (mod: envelope) | utility | streaming | itself | self |
| `frontend/**` (store, hook, components, shared/) | frontend | streaming | none (no frontend exists) | no analog |
| `Dockerfile`, `.dockerignore`, `.env.example`, `.gitignore` | config | n/a | none | no analog |

## Pattern Assignments

### `app/market/cache.py` (add `version`)

Existing mutator style (`cache.py:9-30, 42-43`). Increment `self.version` in `update` and in `remove` only when something was removed.

```python
def __init__(self) -> None:
    self._prices: dict[str, PriceUpdate] = {}

def remove(self, ticker: str) -> None:
    self._prices.pop(ticker, None)
```

Keep: docstrings short, no locks, `X | None` typing.

### `app/market/interface.py` (add attributes)

Abstract members use `@property @abstractmethod` (`interface.py:27-30`). `check_ticker` must be a NON-abstract default `return True` so `SimulatorSource` and existing test doubles keep working. Add `kind`, `last_ok`, `stale_after` the same way.

### `app/market/massive.py` (probe, last_ok, check_ticker)

Core poll pattern to copy and extend (`massive.py:86-107`):

```python
resp = await self._client.get(
    SNAPSHOT_PATH, params={"tickers": ",".join(sorted(self._tickers))}
)
resp.raise_for_status()
prices = parse_snapshot(resp.json())
except httpx.HTTPError as exc:
    log.warning("Massive poll failed: %s", exc)
    return
```

Set `self.last_ok = time.time()` only when `prices` has a tracked ticker (after the loop at `:105-107`). `probe_massive` and `check_ticker` reuse `self._client`, `SNAPSHOT_PATH`, `parse_snapshot`; catch `httpx.HTTPError`/`ValueError` narrowly (real network boundary). Module logger: `log = logging.getLogger(__name__)` (`:10`); `%s` lazy format. Reasons are fixed strings, never `str(exc)`.

### `app/market/factory.py` (`start_market_source`)

Keep `create_market_source` untouched (test_factory depends on it). Copy the env read idiom (`factory.py:11-14`):

```python
api_key = os.getenv("MASSIVE_API_KEY", "").strip()
if api_key:
    poll = float(os.getenv("MASSIVE_POLL_SECONDS", "15"))
    return MassiveSource(cache, api_key, poll_seconds=poll)
return SimulatorSource(cache)
```

Build the `httpx.AsyncClient` once, probe it, pass it as `MassiveSource(..., client=client)` (existing injection point `massive.py:45`); on failure `await client.aclose()` and return `SimulatorSource` plus reason.

### `app/market/stream.py` (batched envelope)

Keep router, `PUSH_SECONDS`, `RETRY_MS`, first `ServerSentEvent(retry=RETRY_MS)` and the thin route (`stream.py:10-13, 23, 33-37`). Replace the per-ticker loop (`:24-30`) with the version-gated key from RESEARCH Pattern 1; `price_events(cache, get_status, interval=...)`. Route passes `lambda: build_status(request.app.state.market_source, note)` (state read via `request.app.state`, as at `:36`).

### `app/main.py`

Keep `lifespan` shape (`main.py:10-22`): build cache, start source, set `app.state.*`, `yield`, `await source.stop()`. Add `init_db`, `tracked_tickers`, `start_market_source` before `yield` (resolves TODO at `:14`). Router include style (`:26`): `app.include_router(...)`. Static mount and the `/api/{path:path}` JSON 404 go LAST (RESEARCH Pattern 7). Health extends `{"status": "ok"}` with `**build_status(...)` (D-05).

### `app/routes/*.py` (route, request-response)

Analog: `app/market/stream.py:10, 33-37` (`APIRouter(prefix="/api/...")`, handler reads `request.app.state`). Follow it; return plain dict/list; errors via `HTTPException(status_code=400|404|409, detail="...")` (readable string, no pydantic `pattern=`).

### `app/context.py`

Analog: `@dataclass(frozen=True, slots=True)` as used for `PriceUpdate` in `app/market/models.py`. Fields `db_path, cache, source, market_note`.

### `app/services/tracking.py` and watchlist service

Idempotent add/remove convention: `SimulatorSource.add_ticker` (`if ticker not in self._prices`) and `remove_ticker` (`pop(ticker, None)`). `sync` diffs `tracked_tickers(db_path)` against `ctx.source.tickers`; the only caller of `add_ticker`/`remove_ticker`. Lookups return `None`, not exceptions; do not wrap internal calls in try/except.

### Tests

- Async tests need no decorator (`asyncio_mode = "auto"`); tests are not annotated.
- Lifespan test pattern (`tests/market/test_app.py:8-13`): `monkeypatch.delenv("MASSIVE_API_KEY", raising=False)`, `async with lifespan(app):`; add `monkeypatch.setenv("DB_PATH", str(tmp_path / "finally.db"))` in a new `tests/conftest.py`.
- ASGI route test (`test_app.py:16-20`): `httpx.ASGITransport(app=app)` with `base_url="http://test"`.
- Generator test helpers (`test_stream.py:14-15, 18-20`): `take(gen, n)`, `price_events(cache, interval=0)`; rewrite assertions to `event.data["prices"]`/`["status"]`, pass a `get_status` lambda.
- No-new-event check (`test_stream.py:33-39`): `pytest.raises(TimeoutError)` around `asyncio.wait_for(anext(gen), 0.05)`.
- Real-HTTP server fixture (`test_stream.py:70-83`) and `data_lines`/`parse` helpers (`:86-94`): reuse; fixture must also set `app.state.market_source` and note (or the status callable's inputs).
- Probe tests: `httpx.MockTransport` helper pattern in `tests/market/test_massive.py:17-24` (`httpx.AsyncClient(base_url="https://api.massive.com", transport=httpx.MockTransport(handler), headers={"Authorization": "Bearer k"})`). Assert reason never contains the key.

## Shared Patterns

### Conventions (apply to all backend files)
Source: `.claude/CLAUDE.md` Conventions. Modern typing (`list[str]`, `X | None`), annotated public signatures, short docstrings, relative imports inside a package, absolute `from app.x import ...` outside, `log = logging.getLogger(__name__)`, `%s` logging, no emojis, no linter config. New packages (`db`, `services`, `routes`) get no barrel `__init__` exports.

### Error handling
`massive.py:99-104`: narrow `except httpx.HTTPError` with `log.warning`; no try/except around internal calls. Missing data is `None`.

### Single source for status
`build_status` used by SSE stream and `/api/health` so they cannot disagree.

### Lifecycle
`asyncio.create_task` in `start()`, cancel plus `contextlib.suppress(asyncio.CancelledError)` in `stop()` (`massive.py:66-72`).

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `app/db/*` (schema.sql, connection.py, watchlist.py) | store | CRUD | No sqlite code yet. Use RESEARCH Pattern 5 (BEGIN IMMEDIATE, INSERT OR IGNORE rowcount seed, `user_version` guard). Place `tests/db/` beside. |
| `app/schemas.py` | utility | transform | No request models yet. One `normalize_ticker()` with `^[A-Z]{1,5}(\.[A-Z])?$`. |
| `frontend/**` | component/store/hook | streaming | No frontend exists. Use RESEARCH Patterns 8-10 and the type block; avoid `src/lib/` (gitignored), use `src/shared/`. |
| `Dockerfile`, `.dockerignore`, `.env.example`, `.gitignore` edits | config | n/a | None exist. Use RESEARCH Pitfall 8 and PLAN.md section 11. |

## Metadata

**Analog search scope:** `backend/app`, `backend/tests`, `backend/scripts` (all 21 tracked files)
**Files scanned:** 21
**Pattern extraction date:** 2026-10-19
**Caveat:** RESEARCH.md was read only to line 542 of 752 (truncated); remaining sections (frontend code, validation architecture) were not consulted.
