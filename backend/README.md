# FinAlly Backend

FastAPI backend (uv project, Python 3.12). Currently implements the market data layer in `app/market/`.

- `interface.py` - `MarketDataSource` abstract base class
- `simulator.py` - GBM simulator (default)
- `massive.py` - Massive REST poller (used when `MASSIVE_API_KEY` is set)
- `cache.py`, `models.py` - shared in-memory price cache
- `stream.py` - `GET /api/stream/prices` (SSE, FastAPI `EventSourceResponse`)
- `factory.py` - picks the source from the environment

```bash
uv sync
uv run pytest
uv run --env-file ../.env uvicorn app.main:app --port 8000
curl -N http://localhost:8000/api/stream/prices
```

Design: `planning/MARKET_DATA_DESIGN.md`. Review: `planning/MARKET_DATA_REVIEW.md`.
