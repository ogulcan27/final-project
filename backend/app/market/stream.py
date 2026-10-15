import asyncio
import json
from collections.abc import AsyncIterator, Awaitable, Callable

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from .cache import PriceCache

router = APIRouter(prefix="/api/stream")

PUSH_SECONDS = 0.5


async def price_events(
    cache: PriceCache,
    is_disconnected: Callable[[], Awaitable[bool]],
    interval: float = PUSH_SECONDS,
) -> AsyncIterator[str]:
    """Yield SSE messages: all tickers first, then only tickers that changed."""
    yield "retry: 1000\n\n"  # EventSource reconnect delay in ms
    last_sent: dict[str, float] = {}
    while not await is_disconnected():
        for update in cache.all():
            if last_sent.get(update.ticker) != update.timestamp:
                last_sent[update.ticker] = update.timestamp
                yield f"data: {json.dumps(update.to_dict())}\n\n"
        await asyncio.sleep(interval)


@router.get("/prices")
async def stream_prices(request: Request) -> StreamingResponse:
    """Long-lived SSE stream of live price updates."""
    return StreamingResponse(
        price_events(request.app.state.price_cache, request.is_disconnected),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
