from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.market import PriceCache, create_market_source
from app.market.seed_data import DEFAULT_TICKERS
from app.market.stream import router as stream_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start the market data source on startup and stop it on shutdown.

    TODO: replace DEFAULT_TICKERS with watchlist UNION open positions from SQLite.
    """
    cache = PriceCache()
    source = create_market_source(cache)
    await source.start(DEFAULT_TICKERS)
    app.state.price_cache = cache
    app.state.market_source = source
    yield
    await source.stop()


app = FastAPI(lifespan=lifespan)
app.include_router(stream_router)


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok"}
