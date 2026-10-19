import asyncio

from app import db
from app.market import PriceCache

from .portfolio import get_portfolio

SNAPSHOT_SECONDS = 30.0


async def record_snapshots(cache: PriceCache, interval: float = SNAPSHOT_SECONDS) -> None:
    """Record the total portfolio value now and then every interval seconds, forever."""
    while True:
        db.insert_snapshot(get_portfolio(cache)["total_value"])
        await asyncio.sleep(interval)
