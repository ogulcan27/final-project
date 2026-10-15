import asyncio
from collections.abc import AsyncIterator

from fastapi import APIRouter, Request
from fastapi.sse import EventSourceResponse, ServerSentEvent

from .cache import PriceCache
from .models import PriceUpdate

router = APIRouter(prefix="/api/stream")

PUSH_SECONDS = 0.5
RETRY_MS = 1000


async def price_events(
    cache: PriceCache, interval: float = PUSH_SECONDS
) -> AsyncIterator[ServerSentEvent]:
    """Yield SSE events forever: all tickers first, then only tickers that changed.

    Every cache write creates a new PriceUpdate, so identity marks a change.
    """
    yield ServerSentEvent(retry=RETRY_MS)
    last_sent: dict[str, PriceUpdate] = {}
    while True:
        for update in cache.all():
            if last_sent.get(update.ticker) is not update:
                last_sent[update.ticker] = update
                yield ServerSentEvent(data=update.to_dict())
        await asyncio.sleep(interval)


@router.get("/prices", response_class=EventSourceResponse)
async def stream_prices(request: Request) -> AsyncIterator[ServerSentEvent]:
    """Long-lived SSE stream of live price updates, with keep-alive pings."""
    async for event in price_events(request.app.state.price_cache):
        yield event
