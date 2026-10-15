# FinAlly Backend

FastAPI backend (uv project). Currently implements the market data layer in `app/market/`.

- `interface.py` - `MarketDataSource` abstract base class
- `simulator.py` - GBM simulator (default)
- `massive.py` - Massive REST poller (used when `MASSIVE_API_KEY` is set)
- `cache.py`, `models.py` - shared in-memory price cache
- `stream.py` - `GET /api/stream/prices` (SSE)
- `factory.py` - picks the source from the environment

```bash
uv sync
uv run pytest
uv run uvicorn app.main:app --port 8000
```

Design: `planning/MARKET_DATA_DESIGN.md`.
