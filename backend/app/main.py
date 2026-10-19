import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app import db
from app.api.portfolio import router as portfolio_router
from app.api.watchlist import router as watchlist_router
from app.llm.router import router as chat_router
from app.market import PriceCache, create_market_source
from app.market.stream import router as stream_router
from app.services import record_snapshots

BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_DIR.parent / ".env")


def startup_tickers() -> list[str]:
    """Watchlist UNION tickers with an open position, watchlist order first."""
    tickers = db.get_watchlist()
    held = [p["ticker"] for p in db.get_positions() if p["ticker"] not in tickers]
    return tickers + held


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Init the DB, start the market source and snapshot task; stop them on shutdown."""
    db.init_db()
    cache = PriceCache()
    source = create_market_source(cache)
    await source.start(startup_tickers())
    app.state.price_cache = cache
    app.state.market_source = source
    snapshots = asyncio.create_task(record_snapshots(cache))
    yield
    snapshots.cancel()
    await source.stop()


app = FastAPI(lifespan=lifespan)
app.include_router(stream_router)
app.include_router(portfolio_router)
app.include_router(watchlist_router)
app.include_router(chat_router)


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok"}


static_dir = Path(os.getenv("STATIC_DIR", BACKEND_DIR / "static"))
if static_dir.is_dir():
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
